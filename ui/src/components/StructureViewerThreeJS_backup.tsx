import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { CrystalStructure } from '../types';
import {
  convertToConventionalCell as localConvertToConventionalCell,
  fractionalToCartesian
} from '../utils/cifParser';
// import { convertToConventionalCell as apiConvertToConventionalCell, checkAPIHealth } from '../utils/apiClient';

interface Props {
  structure: CrystalStructure;
}

type CellType = 'primitive' | 'conventional';

// CPK 原子颜色 (完整版本，覆盖所有118个元素)
const atomColor: Record<string, string> = {
  // 第1周期
  h: '#FFFFFF',   // 1 氢 - 白色
  he: '#D9FFFF',  // 2 氦 - 青色

  // 第2周期
  li: '#CC80FF',  // 3 锂 - 紫色
  be: '#C2FF00',  // 4 铍 - 黄绿色
  b: '#FFB5B5',   // 5 硼 - 粉红色
  c: '#909090',   // 6 碳 - 灰色
  n: '#3050F8',   // 7 氮 - 蓝色
  o: '#FF0D0D',   // 8 氧 - 红色
  f: '#90E050',   // 9 氟 - 绿色
  ne: '#B3E3F5',  // 10 氖 - 浅蓝色

  // 第3周期
  na: '#AB5CF2',  // 11 钠 - 紫色
  mg: '#8AFF00',  // 12 镁 - 绿色
  al: '#BFA6A6',  // 13 铝 - 灰色
  si: '#F0C8A0',  // 14 硅 - 米色
  p: '#FF8000',   // 15 磷 - 橙色
  s: '#FFFF30',   // 16 硫 - 黄色
  cl: '#1FF01F',  // 17 氯 - 绿色
  ar: '#80D1E3',  // 18 氩 - 青色

  // 第4周期
  k: '#8F40D4',   // 19 钾 - 紫色
  ca: '#3DFF00',  // 20 钙 - 绿色
  sc: '#E6E6E6',  // 21 钪 - 浅灰色
  ti: '#BFC2C7',  // 22 钛 - 灰色
  v: '#A6A6AB',   // 23 钒 - 灰色
  cr: '#8A99C7',  // 24 铬 - 蓝灰色
  mn: '#9C7AC7',  // 25 锰 - 紫色
  fe: '#E06633',  // 26 铁 - 橙红色
  co: '#F090A0',  // 27 钴 - 粉色
  ni: '#50D050',  // 28 镍 - 绿色
  cu: '#C88033',  // 29 铜 - 棕色
  zn: '#7D80B0',  // 30 锌 - 蓝灰色
  ga: '#C28F8F',  // 31 镓 - 红棕色
  ge: '#668F8F',  // 32 锗 - 灰绿色
  as: '#BD80E3',  // 33 砷 - 紫色
  se: '#FFA100',  // 34 硒 - 橙色
  br: '#A62929',  // 35 溴 - 深红色
  kr: '#5CB8D1',  // 36 氪 - 青色

  // 第5周期
  rb: '#702EB0',  // 37 铷 - 深紫色
  sr: '#00FF00',  // 38 锶 - 绿色
  y: '#94FFFF',   // 39 钇 - 青色
  zr: '#94E0E0',  // 40 锆 - 青色
  nb: '#73C2C9',  // 41 铌 - 青色
  mo: '#54B5B5',  // 42 钼 - 青色
  tc: '#3B9E9E',  // 43 锝 - 青色
  ru: '#248F8F',  // 44 钌 - 青色
  rh: '#0A7D8C',  // 45 铑 - 青色
  pd: '#006985',  // 46 钯 - 深青色
  ag: '#C0C0C0',  // 47 银 - 银色
  cd: '#FFD98F',  // 48 镉 - 金黄色
  in: '#A67573',  // 49 铟 - 棕色
  sn: '#668080',  // 50 锡 - 灰绿色
  sb: '#9E63B5',  // 51 锑 - 紫色
  te: '#D47A00',  // 52 碲 - 橙色
  i: '#940094',   // 53 碘 - 紫色
  xe: '#429EB0',  // 54 氙 - 青色

  // 第6周期
  cs: '#57178F',  // 55 铯 - 深紫色
  ba: '#00C900',  // 56 钡 - 绿色
  la: '#70D4FF',  // 57 镧 - 浅蓝色
  ce: '#FFFFC7',  // 58 铈 - 浅黄色
  pr: '#D9FFC7',  // 59 镨 - 浅绿色
  nd: '#C7FFC7',  // 60 钕 - 浅绿色
  pm: '#A3FFC7',  // 61 钷 - 浅绿色
  sm: '#8FFFC7',  // 62 钐 - 浅绿色
  eu: '#61FFC7',  // 63 铕 - 浅绿色
  gd: '#45FFC7',  // 64 钆 - 浅绿色
  tb: '#30FFC7',  // 65 铽 - 浅绿色
  dy: '#1FFFC7',  // 66 镝 - 浅绿色
  ho: '#00FF9C',  // 67 钬 - 绿色
  er: '#00E675',  // 68 铒 - 绿色
  tm: '#00D452',  // 69 铥 - 绿色
  yb: '#00BF38',  // 70 镱 - 绿色
  lu: '#00AB24',  // 71 镥 - 绿色
  hf: '#4DC2FF',  // 72 铪 - 浅蓝色
  ta: '#4DA6FF',  // 73 钽 - 蓝色
  w: '#2194D6',   // 74 钨 - 蓝色
  re: '#267DAB',  // 75 铼 - 蓝色
  os: '#266696',  // 76 锇 - 蓝色
  ir: '#175487',  // 77 铱 - 深蓝色
  pt: '#D0D0E0',  // 78 铂 - 浅灰色
  au: '#FFD123',  // 79 金 - 金色
  hg: '#B8B8D0',  // 80 汞 - 浅灰色
  tl: '#A6544D',  // 81 铊 - 棕色
  pb: '#575961',  // 82 铅 - 深灰色
  bi: '#9E4FB5',  // 83 铋 - 紫色
  po: '#AB5C00',  // 84 钋 - 橙棕色
  at: '#754F45',  // 85 砹 - 棕色
  rn: '#428296',  // 86 氡 - 青色

  // 第7周期
  fr: '#420066',  // 87 钫 - 深紫色
  ra: '#007D00',  // 88 镭 - 深绿色
  ac: '#70ABFA',  // 89 锕 - 浅蓝色
  th: '#00BAFF',  // 90 钍 - 青色
  pa: '#00A1FF',  // 91 镤 - 青色
  u: '#008FFF',   // 92 铀 - 蓝色
  np: '#0080FF',  // 93 镄 - 蓝色
  pu: '#006BFF',  // 94 钚 - 蓝色
  am: '#545CF2',  // 95 镅 - 蓝紫色
  cm: '#785CE3',  // 96 锔 - 紫色
  bk: '#8A4FE3',  // 97 锫 - 紫色
  cf: '#A136D4',  // 98 锎 - 紫色
  es: '#B31FD4',  // 99 锿 - 紫色
  fm: '#B31FBA',  // 100 镄 - 紫色
  md: '#B30DA6',  // 101 钔 - 紫色
  no: '#BD0D87',  // 102 锘 - 紫红色
  lr: '#C70066',  // 103 铹 - 红紫色
  rf: '#CC0059',  // 104  - 红色
  db: '#D1004F',  // 105  - 红色
  sg: '#D90045',  // 106  - 红色
  bh: '#E00038',  // 107  - 红色
  hs: '#E6002E',  // 108 is - 红色
  mt: '#EB0026',  // 109 鿏 - 红色
  ds: '#FF0000',  // 110  - 红色
  rg: '#FF1A1A',  // 111 
};

// 元素符号到原子序数的映射
const elementAtomicNumbers: Record<string, number> = {
  h: 1,
  he: 2,
  li: 3,
  be: 4,
  b: 5,
  c: 6,
  n: 7,
  o: 8,
  f: 9,
  ne: 10,
  na: 11,
  mg: 12,
  al: 13,
  si: 14,
  p: 15,
  s: 16,
  cl: 17,
  ar: 18,
  k: 19,
  ca: 20,
  sc: 21,
  ti: 22,
  v: 23,
  cr: 24,
  mn: 25,
  fe: 26,
  co: 27,
  ni: 28,
  cu: 29,
  zn: 30,
  ga: 31,
  ge: 32,
  as: 33,
  se: 34,
  br: 35,
  kr: 36,
  rb: 37,
  sr: 38,
  y: 39,
  zr: 40,
  nb: 41,
  mo: 42,
  tc: 43,
  ru: 44,
  rh: 45,
  pd: 46,
  ag: 47,
  cd: 48,
  in: 49,
  sn: 50,
  sb: 51,
  te: 52,
  i: 53,
  xe: 54,
  cs: 55,
  ba: 56,
  la: 57,
  ce: 58,
  pr: 59,
  nd: 60,
  pm: 61,
  sm: 62,
  eu: 63,
  gd: 64,
  tb: 65,
  dy: 66,
  ho: 67,
  er: 68,
  tm: 69,
  yb: 70,
  lu: 71,
  hf: 72,
  ta: 73,
  w: 74,
  re: 75,
  os: 76,
  ir: 77,
  pt: 78,
  au: 79,
  hg: 80,
  tl: 81,
  pb: 82,
  bi: 83,
  po: 84,
  at: 85,
  rn: 86,
  fr: 87,
  ra: 88,
  ac: 89,
  th: 90,
  pa: 91,
  u: 92,
  np: 93,
  pu: 94,
  am: 95,
  cm: 96,
  bk: 97,
  cf: 98,
  es: 99,
  fm: 100,
  md: 101,
  no: 102,
  lr: 103,
  rf: 104,
  db: 105,
  sg: 106,
  bh: 107,
  hs: 108,
  mt: 109,
  ds: 110,
  rg: 111,
};

const StructureViewerThreeJS: React.FC<Props> = ({ structure }) => {
  const [cellType, setCellType] = useState<CellType>('primitive');
  const [displayStructure, setDisplayStructure] = useState<CrystalStructure>(structure);

  // 检查原子序数是否超过限制 (大于50)
  const filterAtomsByAtomicNumber = (atoms: typeof structure.atoms) => {
    if (!Array.isArray(atoms)) return [];
    
    return atoms.filter(atom => {
      const elementSymbol = atom.element;
      const atomicNumber = elementAtomicNumbers[elementSymbol] || 0;
      return atomicNumber <= 50; // 只显示原子序数小于等于50的元素
    });
  };

  // 过滤后的结构
  const filteredAtoms = filterAtomsByAtomicNumber(structure.atoms);
  const isTooLarge = filteredAtoms.length === 0 && structure.atoms.length > 0;

  // StructureViewerThreeJS 组件初始化

  // 晶胞类型切换
  useEffect(() => {
    console.log('🔄 晶胞类型切换 - cellType:', cellType, 'hasCellTypes:', !!structure.cellTypes);

    if (!structure.cellTypes) {
      // 如果没有cellTypes数据,使用旧的转换逻辑
      console.log('⚠️ 没有cellTypes数据，使用旧的转换逻辑');
      if (cellType === 'primitive') {
        setDisplayStructure({
          ...structure,
          atoms: filterAtomsByAtomicNumber(structure.atoms)
        });
      } else {
        // 优先使用 API 返回的惯胞数据
        if (structure.metadata?.conventionalStructure && Array.isArray(structure.metadata.conventionalStructure.atoms)) {
          console.log('✅ 使用metadata中的惯胞数据');
          setDisplayStructure({
            ...structure.metadata.conventionalStructure,
            atoms: filterAtomsByAtomicNumber(structure.metadata.conventionalStructure.atoms)
          });
        } else {
          // 回退到本地转换
          console.log('🔧 使用本地转换生成惯胞');

          // 检查 structure 是否有 latticeParameters
          if (!structure.latticeParameters) {
            console.error('❌ structure 缺少 latticeParameters，无法转换为惯胞，使用原始结构');
            setDisplayStructure({
              ...structure,
              atoms: filterAtomsByAtomicNumber(structure.atoms)
            });
          } else {
            const converted = localConvertToConventionalCell(structure);
            setDisplayStructure({
              ...converted,
              atoms: filterAtomsByAtomicNumber(converted.atoms)
            });
          }
        }
      }
    } else {
      // 使用新的cellTypes数据
      console.log('✅ 使用cellTypes数据，可用类型:', Object.keys(structure.cellTypes));

      const cellData = structure.cellTypes[cellType];
      if (!cellData || !cellData.latticeParameters || !Array.isArray(cellData.atoms)) {
        console.error(`❌ cellTypes中没有${cellType}数据，可用类型:`, Object.keys(structure.cellTypes));
        // 回退到primitive
        const fallbackData = structure.cellTypes['primitive'];
        if (fallbackData) {
          console.log('🔄 回退到primitive');
          setCellType('primitive');
          return;
        }
        // 无法回退，使用原始结构以避免崩溃
        setDisplayStructure({
          ...structure,
          atoms: filterAtomsByAtomicNumber(Array.isArray(structure.atoms) ? structure.atoms : [])
        });
        return;
      }

      const { a, b, c, alpha, beta, gamma } = cellData.latticeParameters;

      // 将分数坐标转换为笛卡尔坐标
      const cartesianAtoms = (cellData.atoms || []).map(atom => ({
        ...atom,
        position: fractionalToCartesian(
          atom.position as [number, number, number],
          a, b, c, alpha, beta, gamma
        )
      }));

      const newStructure: CrystalStructure = {
        ...structure,
        latticeParameters: cellData.latticeParameters,
        atoms: filterAtomsByAtomicNumber(cartesianAtoms),
        properties: {
          ...structure.properties,
          volume: cellData.volume,
          numAtoms: cellData.numAtoms
        },
        currentCellType: cellType
      };
      console.log(`✅ 已切换到${cellType}，原子数:`, cartesianAtoms.length);
      setDisplayStructure(newStructure);
    }
  }, [structure, cellType]);

  // 分数坐标转笛卡尔坐标 (使用 cifParser 中的函数) - 备用函数

  // 初始化场景
  useEffect(() => {
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer();
    renderer.setSize(window.innerWidth, window.innerHeight);
    document.body.appendChild(renderer.domElement);

    // 添加光源
    const light = new THREE.DirectionalLight(0xffffff, 1);
    light.position.set(1, 1, 1).normalize();
    scene.add(light);

    // 添加轨道控制器
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.25;
    controls.enableZoom = true;

    // 设置相机位置
    camera.position.z = 5;

    // 渲染循环
    const animate = function () {
      requestAnimationFrame(animate);

      controls.update();

      renderer.render(scene, camera);
    };

    animate();

    // 清理函数
    return () => {
      document.body.removeChild(renderer.domElement);
    };
  }, []);

  // 绘制原子 (原子位置已经是笛卡尔坐标)
  const drawAtom = (atoms: typeof structure.atoms) => {
    // 过滤原子序数大于50的原子
    const filteredAtoms = filterAtomsByAtomicNumber(atoms);
    const list = Array.isArray(filteredAtoms) ? filteredAtoms : []
    const atomGroup = new THREE.Group();
    atomGroup.name = 'atoms';
    
    // 计算结构边界
    const bounds = calculateBounds(list);
    
    // 根据结构大小调整原子半径，确保足够可见
    const baseRadius = Math.max(0.3, Math.min(1.2, bounds.size * 0.08));

    list.forEach((atom, index) => {
      // 原子位置已经是笛卡尔坐标,直接使用
      const [x, y, z] = atom.position;
      
      // 使用元素特定的半径，如果没有则使用计算的半径
      const elementRadius = {
        'H': baseRadius * 0.5,
        'C': baseRadius * 0.8,
        'N': baseRadius * 0.8,
        'O': baseRadius * 0.7,
        'S': baseRadius * 1.2,
        'P': baseRadius * 1.1,
        'Fe': baseRadius * 1.4,
        'Cu': baseRadius * 1.3,
        'Al': baseRadius * 1.2
      };
      
      const radius = elementRadius[atom.element as keyof typeof elementRadius] || baseRadius;
      const geometry = new THREE.SphereGeometry(radius, 32, 16);
      const color = atomColor[atom.element.toLowerCase()] || atomColor.default;
      const material = new THREE.MeshStandardMaterial({
        color: new THREE.Color(color),
        roughness: 0.3,
        metalness: 0.1
      });
      const sphere = new THREE.Mesh(geometry, material);
      sphere.position.set(x, y, z);
      sphere.name = `${atom.element}_${index}`;
      sphere.userData = { element: atom.element, position: [x, y, z], index };
      atomGroup.add(sphere);
    });

    return atomGroup;
  };

  // 绘制化学键 (原子位置已经是笛卡尔坐标)
  const drawBand = (atoms: typeof structure.atoms) => {
    // 过滤原子序数大于50的原子
    const filteredAtoms = filterAtomsByAtomicNumber(atoms);
    const list = Array.isArray(filteredAtoms) ? filteredAtoms : []
    const bandGroup = new THREE.Group();
    bandGroup.name = 'bands';

    // 简单的键检测: 距离小于某个阈值的原子之间绘制键
    const bondThreshold = 3.0; // Å

    for (let i = 0; i < list.length; i++) {
      for (let j = i + 1; j < list.length; j++) {
        // 原子位置已经是笛卡尔坐标,直接使用
        const point1 = new THREE.Vector3(...list[i].position);
        const point2 = new THREE.Vector3(...list[j].position);
        const distance = point1.distanceTo(point2);

        if (distance < bondThreshold) {
          // 计算中点
          const midpoint = new THREE.Vector3().addVectors(point1, point2).multiplyScalar(0.5);

          // 创建两个半圆柱 (不同颜色)
          const color1 = atomColor[list[i].element.toLowerCase()] || atomColor.default;
          const color2 = atomColor[list[j].element.toLowerCase()] || atomColor.default;

          // 第一个半圆柱 (原子1到中点)
          const cylinder1 = createCylinder(point1, midpoint, color1);
          cylinder1.name = `band_${i}_mid`;
          bandGroup.add(cylinder1);

          // 第二个半圆柱 (中点到原子2)
          const cylinder2 = createCylinder(midpoint, point2, color2);
          cylinder2.name = `band_mid_${j}`;
          bandGroup.add(cylinder2);
        }
      }
    }

    return bandGroup;
  };

  return (
    <div>
      <h1>Structure Viewer</h1>
      <p>Cell Type: {cellType}</p>
      <button onClick={() => setCellType(cellType === 'primitive' ? 'conventional' : 'primitive')}>
        Toggle Cell Type
      </button>
      {isTooLarge && <p>Structure is too large to display.</p>}
    </div>
  );
};

export default StructureViewerThreeJS;
