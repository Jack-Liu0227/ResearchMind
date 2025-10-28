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

// CPK 原子颜色 (扩展版本，包含更多元素)
const atomColor: Record<string, string> = {
  // 常见非金属
  h: '#FFFFFF',   // 氢 - 白色
  c: '#909090',   // 碳 - 深灰色 (改为更可见的灰色)
  n: '#3050F8',   // 氮 - 蓝色
  o: '#FF0D0D',   // 氧 - 红色
  s: '#FFFF30',   // 硫 - 黄色
  p: '#FF8000',   // 磷 - 橙色
  f: '#90E050',   // 氟 - 绿色
  cl: '#1FF01F',  // 氯 - 绿色
  br: '#A62929',  // 溴 - 深红色
  i: '#940094',   // 碘 - 紫色

  // 碱金属和碱土金属
  li: '#CC80FF',  // 锂 - 紫色
  na: '#AB5CF2',  // 钠 - 紫色
  k: '#8F40D4',   // 钾 - 紫色
  mg: '#8AFF00',  // 镁 - 绿色
  ca: '#3DFF00',  // 钙 - 绿色

  // 过渡金属
  fe: '#E06633',  // 铁 - 橙红色
  cu: '#C88033',  // 铜 - 棕色
  zn: '#7D80B0',  // 锌 - 蓝灰色
  ag: '#C0C0C0',  // 银 - 银色
  au: '#FFD123',  // 金 - 金色
  ni: '#50D050',  // 镍 - 绿色
  co: '#F090A0',  // 钴 - 粉色
  mn: '#9C7AC7',  // 锰 - 紫色
  cr: '#8A99C7',  // 铬 - 蓝灰色
  ti: '#BFC2C7',  // 钛 - 灰色
  v: '#A6A6AB',   // 钒 - 灰色

  // 其他金属
  al: '#BFA6A6',  // 铝 - 灰色
  si: '#F0C8A0',  // 硅 - 米色
  pb: '#575961',  // 铅 - 深灰色
  sn: '#668080',  // 锡 - 灰绿色

  // 半导体和半金属
  as: '#BD80E3',  // 砷 - 紫色
  se: '#FFA100',  // 硒 - 橙色
  te: '#D47A00',  // 碲 - 橙色

  // 稀土元素
  la: '#70D4FF',  // 镧 - 浅蓝色
  ce: '#FFFFC7',  // 铈 - 浅黄色

  // 默认颜色
  default: '#FF1493'  // 深粉色 - 用于未定义的元素
};

const StructureViewerThreeJS: React.FC<Props> = ({ structure }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.OrthographicCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const atomGroupRef = useRef<THREE.Group | null>(null);
  const autoRotateRef = useRef<boolean>(false);

  const [cellType, setCellType] = useState<CellType>('primitive');
  const [showUnitCell, setShowUnitCell] = useState(true);
  const [showBonds, setShowBonds] = useState(true);
  const [showAxisLabels] = useState(true);
  const [displayStructure, setDisplayStructure] = useState<CrystalStructure>(structure);
  const [showDetailedInfo, setShowDetailedInfo] = useState(false);
  const [scale, setScale] = useState(1.0);
  const [autoRotate, setAutoRotate] = useState(false);
  const [panMode, setPanMode] = useState(false);
  const [showHelp, setShowHelp] = useState(false);

  // 检查原子数是否超过限制
  const MAX_ATOMS = 50;
  const atomCount = Array.isArray(structure?.atoms) ? structure.atoms.length : 0;
  const isTooLarge = atomCount > MAX_ATOMS;

  // StructureViewerThreeJS 组件初始化

  // 晶胞类型切换
  useEffect(() => {
    console.log('🔄 晶胞类型切换 - cellType:', cellType, 'hasCellTypes:', !!structure.cellTypes);

    if (!structure.cellTypes) {
      // 如果没有cellTypes数据,使用旧的转换逻辑
      console.log('⚠️ 没有cellTypes数据，使用旧的转换逻辑');
      if (cellType === 'primitive') {
        setDisplayStructure(structure);
      } else {
        // 优先使用 API 返回的惯胞数据
        if (structure.metadata?.conventionalStructure && Array.isArray(structure.metadata.conventionalStructure.atoms)) {
          console.log('✅ 使用metadata中的惯胞数据');
          setDisplayStructure(structure.metadata.conventionalStructure);
        } else {
          // 回退到本地转换
          console.log('🔧 使用本地转换生成惯胞');

          // 检查 structure 是否有 latticeParameters
          if (!structure.latticeParameters) {
            console.error('❌ structure 缺少 latticeParameters，无法转换为惯胞，使用原始结构');
            setDisplayStructure(structure);
          } else {
            const converted = localConvertToConventionalCell(structure);
            setDisplayStructure(converted);
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
          atoms: Array.isArray(structure.atoms) ? structure.atoms : [],
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
        atoms: cartesianAtoms,
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
    if (!containerRef.current) return;

    const width = containerRef.current.clientWidth;
    const height = containerRef.current.clientHeight;

    // 场景
    const scene = new THREE.Scene();
    scene.background = new THREE.Color('#383838');
    sceneRef.current = scene;

    // 计算结构边界以调整相机
    const bounds = calculateBounds(Array.isArray(displayStructure?.atoms) ? displayStructure.atoms : []);
    const structureSize = Math.max(bounds.size, 3); // 最小视野为3单位
    
    // 正交相机 - 根据容器大小和结构大小智能调整视野
    const aspect = width / height;
    const containerSize = Math.min(width, height);
    
    // 根据容器大小调整缩放因子，使用更大的视野让结构显示更小
    let scaleFactor;
    if (containerSize < 300) {
      scaleFactor = 4.0; // 非常小的容器 - 结构显示得更小
    } else if (containerSize < 500) {
      scaleFactor = 3.0; // 中小容器 - 结构显示得更小
    } else {
      scaleFactor = 2.2; // 大容器 - 结构显示得更小
    }
    
    const frustumSize = structureSize * scaleFactor;
    const camera = new THREE.OrthographicCamera(
      -frustumSize * aspect / 2,
      frustumSize * aspect / 2,
      frustumSize / 2,
      -frustumSize / 2,
      0.1,
      1000
    );
    
    // 将相机放置在结构中心的对角线上，根据容器大小调整距离
    const cameraDistance = structureSize * (containerSize < 400 ? 2.0 : 1.5);
    camera.position.set(
      bounds.center.x + cameraDistance,
      bounds.center.y + cameraDistance,
      bounds.center.z + cameraDistance
    );
    camera.lookAt(bounds.center);
    cameraRef.current = camera;
    
    // 相机设置完成

    // 渲染器
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio);
    containerRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // 轨道控制器 - 以结构中心为目标
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.copy(bounds.center); // 设置旋转中心为结构中心
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.minDistance = structureSize * 0.5;
    controls.maxDistance = structureSize * 3;
    controls.enablePan = true; // 启用平移
    controls.update(); // 应用target设置
    controlsRef.current = controls;

    // 环境光
    const ambientLight = new THREE.AmbientLight('#ffffff', 2);
    scene.add(ambientLight);

    // 平行光
    const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
    directionalLight.position.set(1, 1, 1).normalize();
    scene.add(directionalLight);

    // 渲染循环
    const animate = () => {
      requestAnimationFrame(animate);

      // 自动旋转 - 使用ref避免闭包问题
      if (autoRotateRef.current && atomGroupRef.current) {
        atomGroupRef.current.rotation.y += 0.005;
      }

      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // 窗口大小调整
    const handleResize = () => {
      if (!containerRef.current) return;
      const newWidth = containerRef.current.clientWidth;
      const newHeight = containerRef.current.clientHeight;
      const newAspect = newWidth / newHeight;

      camera.left = -frustumSize * newAspect / 2;
      camera.right = frustumSize * newAspect / 2;
      camera.top = frustumSize / 2;
      camera.bottom = -frustumSize / 2;
      camera.updateProjectionMatrix();

      renderer.setSize(newWidth, newHeight);
    };
    window.addEventListener('resize', handleResize);

    // 清理
    return () => {
      window.removeEventListener('resize', handleResize);
      controls.dispose();
      renderer.dispose();
      if (containerRef.current && renderer.domElement) {
        containerRef.current.removeChild(renderer.domElement);
      }
    };
  }, []);

  // 创建文本标签
  const createTextLabel = (labelText: string, color: string, size: number = 1.5) => {
    const canvas = document.createElement('canvas');
    canvas.width = 200;
    canvas.height = 200;
    const context = canvas.getContext('2d');
    if (!context) return null;

    context.clearRect(0, 0, canvas.width, canvas.height);
    context.font = '120px Times New Roman';
    context.fillStyle = color;
    context.fillText(labelText, canvas.width / 2, canvas.height / 2);

    const texture = new THREE.CanvasTexture(canvas);
    texture.premultiplyAlpha = false;
    texture.needsUpdate = true;

    const material = new THREE.SpriteMaterial({
      map: texture,
      alphaTest: 0.2,
      transparent: true
    });
    const sprite = new THREE.Sprite(material);
    sprite.scale.set(size, size, size);

    return sprite;
  };

  // 计算结构边界
  const calculateBounds = (atoms: typeof structure.atoms) => {
    const list = Array.isArray(atoms) ? atoms : []
    if (list.length === 0) return { min: new THREE.Vector3(), max: new THREE.Vector3(), center: new THREE.Vector3(), size: 0 };
    
    let minX = list[0].position[0], maxX = list[0].position[0];
    let minY = list[0].position[1], maxY = list[0].position[1];
    let minZ = list[0].position[2], maxZ = list[0].position[2];
    
    list.forEach(atom => {
      minX = Math.min(minX, atom.position[0]);
      maxX = Math.max(maxX, atom.position[0]);
      minY = Math.min(minY, atom.position[1]);
      maxY = Math.max(maxY, atom.position[1]);
      minZ = Math.min(minZ, atom.position[2]);
      maxZ = Math.max(maxZ, atom.position[2]);
    });
    
    const min = new THREE.Vector3(minX, minY, minZ);
    const max = new THREE.Vector3(maxX, maxY, maxZ);
    const center = new THREE.Vector3().addVectors(min, max).multiplyScalar(0.5);
    const size = Math.max(maxX - minX, maxY - minY, maxZ - minZ);
    
    return { min, max, center, size };
  };

  // 绘制原子 (原子位置已经是笛卡尔坐标)
  const drawAtom = (atoms: typeof structure.atoms) => {
    const list = Array.isArray(atoms) ? atoms : []
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
    const list = Array.isArray(atoms) ? atoms : []
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

  // 创建圆柱体 (化学键)
  const createCylinder = (point1: THREE.Vector3, point2: THREE.Vector3, color: string) => {
    const distance = point1.distanceTo(point2);
    const height = distance;
    const position = point1.clone().add(point2).divideScalar(2);
    const direction = point2.clone().sub(point1).normalize();

    const radiusTop = 0.1;
    const radiusBottom = 0.1;
    const radialSegments = 32;
    const heightSegments = 1;
    const openEnded = false;

    const geometry = new THREE.CylinderGeometry(
      radiusTop,
      radiusBottom,
      height,
      radialSegments,
      heightSegments,
      openEnded
    );

    const material = new THREE.MeshStandardMaterial({
      color: new THREE.Color(color),
      roughness: 0,
      metalness: 0
    });

    const cylinder = new THREE.Mesh(geometry, material);
    cylinder.position.copy(position);
    cylinder.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction);

    return cylinder;
  };

  // 绘制晶胞边框 (使用 displayStructure 的晶格参数)
  const drawLattice = () => {
    const latticeGroup = new THREE.Group();
    latticeGroup.name = 'lattice';

    // 使用 displayStructure 的晶格参数 (已经根据 cellType 转换过)
    const lpAny = (displayStructure as any)?.latticeParameters;
    const hasLP = lpAny && typeof lpAny.a === 'number' && typeof lpAny.b === 'number' && typeof lpAny.c === 'number' && typeof lpAny.alpha === 'number' && typeof lpAny.beta === 'number' && typeof lpAny.gamma === 'number';
    if (!hasLP) {
      return latticeGroup;
    }
    const { a, b, c, alpha, beta, gamma } = lpAny as { a: number; b: number; c: number; alpha: number; beta: number; gamma: number };
    const alphaRad = (alpha * Math.PI) / 180;
    const betaRad = (beta * Math.PI) / 180;
    const gammaRad = (gamma * Math.PI) / 180;

    const v1 = [a, 0, 0];
    const v2 = [
      b * Math.cos(gammaRad),
      b * Math.sin(gammaRad),
      0
    ];
    const v3 = [
      c * Math.cos(betaRad),
      c * (Math.cos(alphaRad) - Math.cos(betaRad) * Math.cos(gammaRad)) / Math.sin(gammaRad),
      c * Math.sqrt(1 - Math.cos(betaRad) ** 2 - ((Math.cos(alphaRad) - Math.cos(betaRad) * Math.cos(gammaRad)) / Math.sin(gammaRad)) ** 2)
    ];

    // 计算8个顶点
    const points = [];
    for (let n1 = 0; n1 <= 1; n1++) {
      for (let n2 = 0; n2 <= 1; n2++) {
        for (let n3 = 0; n3 <= 1; n3++) {
          const x = n1 * v1[0] + n2 * v2[0] + n3 * v3[0];
          const y = n1 * v1[1] + n2 * v2[1] + n3 * v3[1];
          const z = n1 * v1[2] + n2 * v2[2] + n3 * v3[2];
          points.push(x, y, z);
        }
      }
    }

    const vertices = new Float32Array(points);
    const edges = new Uint16Array([
      0, 1, 0, 2, 0, 4,
      1, 3, 1, 5,
      2, 3, 2, 6,
      3, 7,
      4, 5, 4, 6,
      5, 7,
      6, 7
    ]);

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
    geometry.setIndex(new THREE.BufferAttribute(edges, 1));

    const material = new THREE.LineBasicMaterial({ color: 0xffffff });
    const lineSegments = new THREE.LineSegments(geometry, material);
    latticeGroup.add(lineSegments);

    // 绘制坐标轴 OA, OB, OC
    const drawAxisLine = (toArr: number[], color: string, text: string) => {
      const points = [];
      points.push(new THREE.Vector3(0, 0, 0));
      points.push(new THREE.Vector3(toArr[0], toArr[1], toArr[2]));
      const lineGeometry = new THREE.BufferGeometry().setFromPoints(points);
      const lineMaterial = new THREE.LineBasicMaterial({ color });
      const line = new THREE.Line(lineGeometry, lineMaterial);
      latticeGroup.add(line);

      // 添加文本标签
      const label = createTextLabel(text, color);
      if (label) {
        label.position.set(toArr[0] - 0.2, toArr[1] - 0.2, toArr[2] - 0.2);
        latticeGroup.add(label);
      }
    };

    // OA (红色)
    drawAxisLine(v1, 'red', 'a');
    // OB (绿色)
    drawAxisLine(v2, 'green', 'b');
    // OC (蓝色)
    drawAxisLine(v3, 'blue', 'c');
    // O (白色)
    const originLabel = createTextLabel('o', '#fff');
    if (originLabel) {
      originLabel.position.set(-0.2, -0.2, -0.2);
      latticeGroup.add(originLabel);
    }

    return latticeGroup;
  };

  // 更新结构
  useEffect(() => {
    if (!sceneRef.current) return;

    const scene = sceneRef.current;

    // 移除旧的原子组
    if (atomGroupRef.current) {
      scene.remove(atomGroupRef.current);
    }

    // 创建新的结构组
    const structureGroup = new THREE.Group();
    structureGroup.name = 'structure';

    // 使用 displayStructure (已经根据 cellType 转换过)
    const atomGroup = drawAtom(displayStructure.atoms);
    structureGroup.add(atomGroup);

    // 添加化学键
    if (showBonds) {
      const bandGroup = drawBand(displayStructure.atoms);
      structureGroup.add(bandGroup);
    }

    // 添加晶胞边框
    if (showUnitCell) {
      const lattice = drawLattice();
      structureGroup.add(lattice);
    }

    // 计算边界并居中
    const box = new THREE.Box3().setFromObject(structureGroup);
    const center = box.getCenter(new THREE.Vector3());
    structureGroup.position.sub(center);

    scene.add(structureGroup);
    atomGroupRef.current = structureGroup;

  }, [displayStructure, showUnitCell, showBonds, showAxisLabels]);

  // 同步autoRotate到ref
  useEffect(() => {
    autoRotateRef.current = autoRotate;
  }, [autoRotate]);

  // 应用缩放
  useEffect(() => {
    if (atomGroupRef.current) {
      atomGroupRef.current.scale.set(scale, scale, scale);
    }
  }, [scale]);

  // 切换移动模式
  useEffect(() => {
    if (controlsRef.current) {
      if (panMode) {
        // 移动模式：禁用旋转，启用平移
        controlsRef.current.enableRotate = false;
        controlsRef.current.enablePan = true;
        // 将左键设置为平移
        controlsRef.current.mouseButtons = {
          LEFT: THREE.MOUSE.PAN,
          MIDDLE: THREE.MOUSE.DOLLY,
          RIGHT: THREE.MOUSE.PAN
        };
      } else {
        // 正常模式：启用旋转
        controlsRef.current.enableRotate = true;
        controlsRef.current.enablePan = true;
        // 恢复默认鼠标按钮
        controlsRef.current.mouseButtons = {
          LEFT: THREE.MOUSE.ROTATE,
          MIDDLE: THREE.MOUSE.DOLLY,
          RIGHT: THREE.MOUSE.PAN
        };
      }
    }
  }, [panMode]);

  return (
    <div className="w-full h-full relative bg-gray-800">
      {/* 紧凑的控制面板 - 横向布局 */}
      <div className="absolute top-4 right-4 z-10 bg-white rounded-lg shadow-lg px-2 py-1.5">
        <div className="flex items-center space-x-1">
          {/* 缩放控制 */}
          <button
            onClick={() => {
              setScale(Math.max(0.1, scale - 0.1));
              setAutoRotate(false); // 停止自动旋转
            }}
            className="p-1 hover:bg-gray-100 rounded text-gray-600"
            title="缩小"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7" />
            </svg>
          </button>
          <span className="text-xs text-gray-600 min-w-[2.5rem] text-center px-1">
            {scale.toFixed(1)}x
          </span>
          <button
            onClick={() => {
              setScale(Math.min(3.0, scale + 0.1));
              setAutoRotate(false); // 停止自动旋转
            }}
            className="p-1 hover:bg-gray-100 rounded text-gray-600"
            title="放大"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m3-3H7" />
            </svg>
          </button>

          {/* 分隔线 */}
          <div className="w-px h-4 bg-gray-300 mx-1"></div>

          {/* 显示控制 */}
          <button
            onClick={() => setAutoRotate(!autoRotate)}
            className={`p-1 rounded transition-colors ${autoRotate ? 'bg-blue-100 text-blue-600' : 'hover:bg-gray-100 text-gray-600'}`}
            title="自动旋转"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>

          <button
            onClick={() => {
              setPanMode(!panMode);
              if (!panMode) setAutoRotate(false); // 进入移动模式时停止自动旋转
            }}
            className={`p-1 rounded transition-colors ${panMode ? 'bg-purple-100 text-purple-600' : 'hover:bg-gray-100 text-gray-600'}`}
            title="移动模式（左键拖拽移动）"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
            </svg>
          </button>

          <button
            onClick={() => {
              setShowBonds(!showBonds);
              setAutoRotate(false); // 停止自动旋转
            }}
            className={`px-1.5 py-1 text-xs rounded transition-colors ${showBonds ? 'bg-blue-100 text-blue-600' : 'hover:bg-gray-100 text-gray-600'}`}
            title="显示化学键"
          >
            键
          </button>

          <button
            onClick={() => {
              setShowUnitCell(!showUnitCell);
              setAutoRotate(false); // 停止自动旋转
            }}
            className={`px-1.5 py-1 text-xs rounded transition-colors ${showUnitCell ? 'bg-blue-100 text-blue-600' : 'hover:bg-gray-100 text-gray-600'}`}
            title="显示晶胞框"
          >
            框
          </button>

          {/* 分隔线 */}
          <div className="w-px h-4 bg-gray-300 mx-1"></div>

          {/* 晶胞类型切换 */}
          <button
            onClick={() => {
              setCellType('primitive');
              setAutoRotate(false); // 停止自动旋转
            }}
            className={`px-1.5 py-1 text-xs rounded transition-colors ${
              cellType === 'primitive'
                ? 'bg-green-100 text-green-600'
                : 'hover:bg-gray-100 text-gray-600'
            }`}
            title={structure.cellTypes ? `原胞 (${structure.cellTypes.primitive.numAtoms} 原子)` : '原胞'}
          >
            原胞
          </button>
          <button
            onClick={() => {
              if (structure.cellTypes || structure.metadata?.conventionalStructure) {
                setCellType('conventional');
                setAutoRotate(false); // 停止自动旋转
              }
            }}
            disabled={!structure.cellTypes && !structure.metadata?.conventionalStructure}
            className={`px-1.5 py-1 text-xs rounded transition-colors ${
              cellType === 'conventional'
                ? 'bg-green-100 text-green-600'
                : (!structure.cellTypes && !structure.metadata?.conventionalStructure)
                ? 'bg-gray-50 text-gray-300 cursor-not-allowed'
                : 'hover:bg-gray-100 text-gray-600'
            }`}
            title={
              structure.cellTypes
                ? `惯胞 (${structure.cellTypes.conventional.numAtoms} 原子)`
                : structure.metadata?.conventionalStructure
                ? '惯胞'
                : '惯胞数据不可用'
            }
          >
            惯胞
          </button>

          {/* 分隔线 */}
          <div className="w-px h-4 bg-gray-300 mx-1"></div>

          {/* 详情按钮 */}
          <button
            onClick={() => {
              setShowDetailedInfo(!showDetailedInfo);
              setAutoRotate(false); // 停止自动旋转
            }}
            className={`px-1.5 py-1 text-xs rounded transition-colors ${
              showDetailedInfo ? 'bg-gray-100 text-gray-600' : 'hover:bg-gray-100 text-gray-600'
            }`}
            title={showDetailedInfo ? '隐藏详情' : '显示详情'}
          >
            {showDetailedInfo ? '隐藏' : '详情'}
          </button>

          {/* 帮助按钮 */}
          <button
            onClick={() => setShowHelp(!showHelp)}
            className={`p-1 rounded transition-colors ${showHelp ? 'bg-blue-100 text-blue-600' : 'hover:bg-gray-100 text-gray-600'}`}
            title="操作说明"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </button>
        </div>
      </div>

      {/* 结构信息面板 - 仅在展开时显示 */}
      {showDetailedInfo && (
        <div className="absolute top-16 right-4 z-10 bg-white rounded-lg shadow-lg p-3 max-w-xs">
          <div className="text-xs text-gray-600 space-y-1">
            <div className="font-medium text-gray-900 mb-2">结构信息</div>
            <div>化学式: {structure.formula}</div>
            <div>空间群: {structure.spaceGroup}
              {displayStructure.properties?.spaceGroupNumber &&
                ` (No. ${displayStructure.properties.spaceGroupNumber})`}
            </div>
            {displayStructure.properties?.crystalSystem && (
              <div>晶系: {displayStructure.properties.crystalSystem}</div>
            )}
            <div className="flex items-center gap-2">
              <span>晶胞类型:</span>
              <span className={`px-1.5 py-0.5 rounded text-xs ${
                cellType === 'primitive'
                  ? 'bg-green-100 text-green-700'
                  : 'bg-blue-100 text-blue-700'
              }`}>
                {cellType === 'primitive' ? '原胞' : '惯胞'}
              </span>
            </div>
            <div>原子数: {displayStructure.properties?.numAtoms || displayStructure.atoms.length}</div>
            {displayStructure.properties?.numSites && (
              <div>位点数: {displayStructure.properties.numSites}</div>
            )}

            {displayStructure.latticeParameters && (
              <div className="mt-2 pt-2 border-t border-gray-200 space-y-1">
                <div className="font-medium">晶格参数:</div>
                <div>a = {displayStructure.latticeParameters.a.toFixed(3)} Å</div>
                <div>b = {displayStructure.latticeParameters.b.toFixed(3)} Å</div>
                <div>c = {displayStructure.latticeParameters.c.toFixed(3)} Å</div>
                <div>α = {displayStructure.latticeParameters.alpha.toFixed(2)}°</div>
                <div>β = {displayStructure.latticeParameters.beta.toFixed(2)}°</div>
                <div>γ = {displayStructure.latticeParameters.gamma.toFixed(2)}°</div>

                {displayStructure.properties?.volume && (
                  <div className="mt-1">体积: {displayStructure.properties.volume.toFixed(2)} Å³</div>
                )}
                {displayStructure.properties?.density && (
                  <div>密度: {displayStructure.properties.density.toFixed(2)} g/cm³</div>
                )}
              </div>
            )}

            <div className="mt-2 pt-2 border-t border-gray-200">
              <div className="font-medium">原子列表:</div>
              <div className="max-h-40 overflow-y-auto">
                {displayStructure.atoms.map((atom, index) => (
                  <div key={index} className="text-xs">
                    {atom.element}: ({atom.position[0].toFixed(2)}, {atom.position[1].toFixed(2)}, {atom.position[2].toFixed(2)})
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-2 text-gray-500 text-xs">
              拖拽旋转 | 滚轮缩放
            </div>
          </div>
        </div>
      )}

      {/* 帮助面板 */}
      {showHelp && (
        <div className="absolute bottom-4 left-4 z-10 bg-white rounded-lg shadow-lg p-4 max-w-xs">
          <h3 className="text-sm font-semibold text-gray-800 mb-2">🖱️ 鼠标操作</h3>
          <div className="space-y-1.5 text-xs text-gray-600">
            <div className="flex items-start">
              <span className="font-medium min-w-[5rem]">正常模式:</span>
              <span></span>
            </div>
            <div className="flex items-start ml-4">
              <span className="font-medium min-w-[4rem]">左键拖拽:</span>
              <span className={!panMode ? 'text-blue-600 font-semibold' : ''}>旋转结构</span>
            </div>
            <div className="flex items-start ml-4">
              <span className="font-medium min-w-[4rem]">右键拖拽:</span>
              <span>平移/移动结构</span>
            </div>
            <div className="flex items-start ml-4">
              <span className="font-medium min-w-[4rem]">滚轮:</span>
              <span>缩放视图</span>
            </div>

            <div className="flex items-start mt-2">
              <span className="font-medium min-w-[5rem]">移动模式:</span>
              <span></span>
            </div>
            <div className="flex items-start ml-4">
              <span className="font-medium min-w-[4rem]">左键拖拽:</span>
              <span className={panMode ? 'text-purple-600 font-semibold' : ''}>平移/移动结构</span>
            </div>
            <div className="flex items-start ml-4">
              <span className="font-medium min-w-[4rem]">右键拖拽:</span>
              <span className={panMode ? 'text-purple-600 font-semibold' : ''}>平移/移动结构</span>
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-gray-200">
            <p className="text-xs text-gray-500">
              💡 提示：点击移动按钮切换到移动模式，左键即可移动结构
            </p>
            <p className="text-xs text-gray-500 mt-1">
              ⚠️ 点击其他按钮会自动停止自动旋转
            </p>
          </div>
        </div>
      )}

      {/* Three.js 容器 */}
      {isTooLarge ? (
        <div className="w-full h-full flex items-center justify-center bg-gray-50" style={{ minHeight: '500px' }}>
          <div className="text-center p-8 max-w-md">
            <div className="text-6xl mb-4">⚠️</div>
            <h3 className="text-xl font-semibold text-gray-800 mb-2">
              结构过大，无法显示
            </h3>
            <p className="text-gray-600 mb-4">
              该结构包含 <span className="font-bold text-red-600">{atomCount}</span> 个原子，
              超过了显示限制（{MAX_ATOMS} 个原子）。
            </p>
            <p className="text-sm text-gray-500">
              为了保证性能，我们不显示原子数超过 {MAX_ATOMS} 的结构。
              您仍然可以下载 CIF 文件并使用专业软件查看。
            </p>
          </div>
        </div>
      ) : (
        <div
          ref={containerRef}
          className="w-full h-full"
          style={{ minHeight: '500px' }}
        />
      )}
    </div>
  );
};

export default StructureViewerThreeJS;

