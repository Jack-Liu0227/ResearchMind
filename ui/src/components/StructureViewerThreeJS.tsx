import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { CrystalStructure } from '../types';
import {
  convertToConventionalCell as localConvertToConventionalCell,
  fractionalToCartesian,
  cartesianToFractional
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
  np: '#0080FF',  // 93 镎 - 蓝色
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
  rf: '#CC0059',  // 104 𬬻 - 红色
  db: '#D1004F',  // 105 𬭊 - 红色
  sg: '#D90045',  // 106 𬭳 - 红色
  bh: '#E00038',  // 107 𬭛 - 红色
  hs: '#E6002E',  // 108 𬭶 - 红色
  mt: '#EB0026',  // 109 鿏 - 红色
  ds: '#FF0000',  // 110 𫟼 - 红色
  rg: '#FF1A1A',  // 111 𬬭 - 红色
  cn: '#FF3333',  // 112 鿔 - 红色
  nh: '#FF4D4D',  // 113 鿭 - 红色
  fl: '#FF6666',  // 114 𫓧 - 红色
  mc: '#FF8080',  // 115 镆 - 红色
  lv: '#FF9999',  // 116 𫟷 - 红色
  ts: '#FFB3B3',  // 117 鿬 - 红色
  og: '#FFCCCC',  // 118 鿫 - 红色

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

  const [cellType, setCellType] = useState<CellType>('conventional'); // Default to conventional for better visualization
  const [showUnitCell, setShowUnitCell] = useState(true);
  const [showBonds, setShowBonds] = useState(true);
  const [showAxisLabels] = useState(true);
  const [displayStructure, setDisplayStructure] = useState<CrystalStructure>(structure);
  const [showDetailedInfo, setShowDetailedInfo] = useState(false);
  const [scale, setScale] = useState(1.0);
  const [autoRotate, setAutoRotate] = useState(false);
  const [panMode, setPanMode] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const [fillBoundaries, setFillBoundaries] = useState(true); // New state for boundary completion
  const [showLabels, setShowLabels] = useState(false); // Toggle for atom labels

  const getUniqueElements = (atoms: any[]) => {
    const elements = new Set<string>();
    atoms.forEach(atom => elements.add(atom.element));
    return Array.from(elements).sort();
  };

  const uniqueElements = getUniqueElements(displayStructure?.atoms || []);

  // Check limits
  const MAX_ATOMS = 2000;
  const atomCount = Array.isArray(structure?.atoms) ? structure.atoms.length : 0;
  const isTooLarge = atomCount > MAX_ATOMS;

  // Use ref to track initialization to avoid re-renders
  const isInitializedRef = useRef(false);

  // Switch cell type and process structure
  useEffect(() => {
    let latticeParams: any = null;
    let baseAtomsFrac: { element: string, position: [number, number, number] }[] = [];
    let currentCellStructure: CrystalStructure | null = null;

    // 0. Set boundary preference based on cellType
    const shouldFillBoundaries = (cellType === 'conventional');
    if (fillBoundaries !== shouldFillBoundaries) {
      setFillBoundaries(shouldFillBoundaries);
    }

    // 1. Try to get data from pre-calculated cellTypes response
    if (structure.cellTypes && structure.cellTypes[cellType]) {
      const cellData = structure.cellTypes[cellType];
      if (cellData && cellData.latticeParameters && Array.isArray(cellData.atoms)) {
        latticeParams = cellData.latticeParameters;
        baseAtomsFrac = cellData.atoms.map((a: any) => ({
          element: a.element,
          position: a.position as [number, number, number]
        }));
        currentCellStructure = {
          ...structure,
          latticeParameters: cellData.latticeParameters,
          properties: { ...structure.properties, volume: cellData.volume, numAtoms: cellData.numAtoms },
          currentCellType: cellType
        };
        console.log(`✅ 使用预计算的 ${cellType} 胞数据`);
      }
    }

    // 2. Fallback if not found in cellTypes
    if (!currentCellStructure) {
      console.log(`🔧 ${cellType} 胞数据未预计算，尝试回退逻辑`);
      if (cellType === 'conventional') {
        // Try metadata first
        if (structure.metadata?.conventionalStructure && Array.isArray(structure.metadata.conventionalStructure.atoms)) {
          currentCellStructure = structure.metadata.conventionalStructure;
          console.log('✅ 使用metadata中的惯胞数据');
        }
        // Try local conversion
        else if (structure.latticeParameters) {
          console.log('🔧 使用本地转换生成惯胞');
          currentCellStructure = localConvertToConventionalCell(structure);
        } else {
          console.error('❌ structure 缺少 latticeParameters，无法转换为惯胞，使用原始结构');
        }
      }

      // If still null (or if cellType is primitive), use original structure (assuming it is primitive-like or best effort)
      if (!currentCellStructure) {
        currentCellStructure = structure;
        console.log('⚠️ 回退到原始结构');
      }

      // Now extract latticeParams and baseAtomsFrac from this fallback structure
      latticeParams = currentCellStructure.latticeParameters;
      if (latticeParams && currentCellStructure.atoms) {
        // Convert Cartesian atoms to Fractional for boundary generation logic
        baseAtomsFrac = currentCellStructure.atoms.map(atom => {
          const frac = cartesianToFractional(
            atom.position,
            latticeParams.a, latticeParams.b, latticeParams.c,
            latticeParams.alpha, latticeParams.beta, latticeParams.gamma
          );
          return { element: atom.element, position: frac };
        });
      } else {
        console.warn('⚠️ 无法获取晶格参数或原子数据，跳过边界填充');
        baseAtomsFrac = []; // Ensure it's empty if no lattice params
      }
    }

    // 3. Apply Boundary Completion (Ghost Atoms)
    let finalAtomsCartesian: any[] = [];
    const existingPos = new Set<string>(); // Set to track existing positions and avoid duplicates

    if (!shouldFillBoundaries && currentCellStructure) {
      // If not filling boundaries (e.g., primitive cell), just use the atoms from the determined structure
      finalAtomsCartesian = currentCellStructure.atoms || [];
    }
    else if (latticeParams && baseAtomsFrac.length > 0) {
      const { a, b, c, alpha, beta, gamma } = latticeParams;

      baseAtomsFrac.forEach((atom, idx) => {
        const [u, v, w] = atom.position;

        // Normalize to [0, 1) to handle periodicity consistently
        const u0 = (u % 1.0 + 1.0) % 1.0;
        const v0 = (v % 1.0 + 1.0) % 1.0;
        const w0 = (w % 1.0 + 1.0) % 1.0;

        const shifts = [[0, 0, 0]]; // Base atom

        if (shouldFillBoundaries) {
          // Epsilon for boundary detection.
          const eps = 0.05;
          const u_shifts = (u0 < eps) ? [0, 1] : (u0 > 1 - eps ? [-1, 0] : [0]);
          const v_shifts = (v0 < eps) ? [0, 1] : (v0 > 1 - eps ? [-1, 0] : [0]);
          const w_shifts = (w0 < eps) ? [0, 1] : (w0 > 1 - eps ? [-1, 0] : [0]);

          // Generate combinations
          for (const du of u_shifts) {
            for (const dv of v_shifts) {
              for (const dw of w_shifts) {
                if (du === 0 && dv === 0 && dw === 0) continue; // Already added as base
                shifts.push([du, dv, dw]);
              }
            }
          }
        }

        // Convert all shifts to Cartesian
        shifts.forEach(([du, dv, dw]) => {
          const finalFrac: [number, number, number] = [u0 + du, v0 + dv, w0 + dw];
          const cartPos = fractionalToCartesian(finalFrac, a, b, c, alpha, beta, gamma);

          // Deduplicate
          const key = `${cartPos[0].toFixed(3)},${cartPos[1].toFixed(3)},${cartPos[2].toFixed(3)}`;
          if (!existingPos.has(key)) {
            existingPos.add(key);
            finalAtomsCartesian.push({
              element: atom.element,
              position: cartPos,
              originalIndex: idx
            });
          }
        });
      });
    } else {
      // Fallback if calculations failed or no lattice params for boundary fill
      finalAtomsCartesian = currentCellStructure?.atoms || [];
    }

    // 4. Update Display
    if (currentCellStructure) {
      console.log(`✅ 已切换到${cellType}，显示原子数:`, finalAtomsCartesian.length);
      setDisplayStructure({
        ...currentCellStructure,
        atoms: finalAtomsCartesian
      });
    }

  }, [structure, cellType]); // Removed fillBoundaries from dependency to avoid loop, we derive it.

  // 分数坐标转笛卡尔坐标 (使用 cifParser 中的函数) - 备用函数

  // 初始化场景
  useEffect(() => {
    if (!containerRef.current) return;

    // 使用 ResizeObserver 监听容器尺寸变化
    const initializeScene = () => {
      console.log('🎬 initializeScene called');

      if (!containerRef.current) {
        console.warn('⚠️ containerRef.current is null');
        return;
      }

      const width = containerRef.current.clientWidth;
      const height = containerRef.current.clientHeight;

      // 如果容器尺寸为0，说明还没有完成布局，等待下次尺寸变化
      if (width === 0 || height === 0) {
        console.warn('⚠️ Container size is 0, waiting for layout...', { width, height });
        isInitializedRef.current = false;
        return;
      }

      // 如果已经初始化过，不要重复初始化
      if (isInitializedRef.current && rendererRef.current) {
        console.log('✅ Already initialized, skipping...');
        return;
      }

      // 如果有旧的渲染器，先清理
      if (rendererRef.current) {
        console.log('🧹 Cleaning up existing renderer...');
        if (controlsRef.current) {
          controlsRef.current.dispose();
        }
        rendererRef.current.dispose();
        if (containerRef.current && rendererRef.current.domElement.parentNode === containerRef.current) {
          containerRef.current.removeChild(rendererRef.current.domElement);
        }
      }

      console.log('🚀 Initializing Three.js with container size:', { width, height });

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

        // 检查尺寸是否有效
        if (newWidth === 0 || newHeight === 0) return;

        const newAspect = newWidth / newHeight;

        camera.left = -frustumSize * newAspect / 2;
        camera.right = frustumSize * newAspect / 2;
        camera.top = frustumSize / 2;
        camera.bottom = -frustumSize / 2;
        camera.updateProjectionMatrix();

        renderer.setSize(newWidth, newHeight);
      };
      window.addEventListener('resize', handleResize);

      // 标记为已初始化
      isInitializedRef.current = true;
      console.log('Three.js initialization complete');
    };

    // 使用 ResizeObserver 监听容器尺寸变化
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        console.log('📏 Container resized:', { width, height, isInitialized: isInitializedRef.current });

        // 如果尺寸有效且未初始化，则初始化场景
        if (width > 0 && height > 0 && !isInitializedRef.current) {
          console.log('🚀 Triggering initialization from ResizeObserver');
          initializeScene();
        } else if (width === 0 || height === 0) {
          console.warn('⚠️ Container has zero size, cannot initialize');
        } else if (isInitializedRef.current) {
          console.log('✅ Already initialized, skipping');
        }
      }
    });

    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }

    // 立即尝试初始化（如果容器已经有尺寸）
    initializeScene();

    // 清理
    return () => {
      resizeObserver.disconnect();
      window.removeEventListener('resize', () => { });

      // 清理场景中的所有对象
      if (atomGroupRef.current) {
        disposeObject(atomGroupRef.current);
      }
      if (sceneRef.current) {
        sceneRef.current.traverse((child) => {
          if (child instanceof THREE.Mesh || child instanceof THREE.Line || child instanceof THREE.LineSegments || child instanceof THREE.Sprite) {
            if (child.geometry) child.geometry.dispose();
            if (child.material) {
              if (Array.isArray(child.material)) {
                child.material.forEach((m) => {
                  if (m.map) m.map.dispose();
                  m.dispose();
                });
              } else {
                if (child.material.map) child.material.map.dispose();
                child.material.dispose();
              }
            }
          }
        });
      }

      if (controlsRef.current) {
        controlsRef.current.dispose();
      }
      if (rendererRef.current) {
        rendererRef.current.dispose();
        if (containerRef.current && rendererRef.current.domElement.parentNode === containerRef.current) {
          containerRef.current.removeChild(rendererRef.current.domElement);
        }
      }
      isInitializedRef.current = false;
    };
  }, []);

  // 创建文本标签
  const createTextLabel = (labelText: string, color: string, size: number = 1.0) => {
    const canvas = document.createElement('canvas');
    canvas.width = 256;
    canvas.height = 256;
    const context = canvas.getContext('2d');
    if (!context) return null;

    context.clearRect(0, 0, canvas.width, canvas.height);
    context.font = 'bold 160px Arial';
    context.textAlign = 'center';
    context.textBaseline = 'middle';

    // 描边（黑色）
    context.lineWidth = 8;
    context.strokeStyle = 'rgba(0,0,0, 0.8)';
    context.strokeText(labelText, canvas.width / 2, canvas.height / 2);

    // 填充
    context.fillStyle = color;
    context.fillText(labelText, canvas.width / 2, canvas.height / 2);

    const texture = new THREE.CanvasTexture(canvas);
    texture.premultiplyAlpha = false;
    texture.needsUpdate = true;

    const material = new THREE.SpriteMaterial({
      map: texture,
      transparent: true,
      depthTest: false, // 关键：禁用深度测试，使其总是位于顶层
      depthWrite: false
    });

    const sprite = new THREE.Sprite(material);
    sprite.scale.set(size, size, size);
    sprite.renderOrder = 999; // 确保最后渲染

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

      // Add label if enabled
      if (showLabels) {
        const sprite = createTextLabel(atom.element, '#FFFFFF', 0.8);
        if (sprite) {
          sprite.position.set(x, y, z);
          atomGroup.add(sprite);
        }
      }
    });

    return atomGroup;
  };

  // Covalent radii (in Angstroms) for bond calculation
  const covalentRadii: Record<string, number> = {
    H: 0.31, He: 0.28, Li: 1.28, Be: 0.96, B: 0.84, C: 0.76, N: 0.71, O: 0.66, F: 0.57, Ne: 0.58,
    Na: 1.66, Mg: 1.41, Al: 1.21, Si: 1.11, P: 1.07, S: 1.05, Cl: 1.02, Ar: 1.06,
    K: 2.03, Ca: 1.76, Sc: 1.70, Ti: 1.60, V: 1.53, Cr: 1.39, Mn: 1.39, Fe: 1.32, Co: 1.26, Ni: 1.24, Cu: 1.32, Zn: 1.22,
    Ga: 1.22, Ge: 1.20, As: 1.19, Se: 1.20, Br: 1.20, Kr: 1.16, Rb: 2.20, Sr: 1.95, Y: 1.90, Zr: 1.75, Nb: 1.64, Mo: 1.54,
    Tc: 1.47, Ru: 1.46, Rh: 1.42, Pd: 1.39, Ag: 1.45, Cd: 1.44, In: 1.42, Sn: 1.39, Sb: 1.39, Te: 1.38, I: 1.39, Xe: 1.40,
    Cs: 2.44, Ba: 2.15, La: 2.07, Ce: 2.04, Pr: 2.03, Nd: 2.01, Pm: 1.99, Sm: 1.98, Eu: 1.98, Gd: 1.96, Tb: 1.94, Dy: 1.92,
    Ho: 1.92, Er: 1.89, Tm: 1.90, Yb: 1.87, Lu: 1.87, Hf: 1.75, Ta: 1.70, W: 1.62, Re: 1.51, Os: 1.44, Ir: 1.41, Pt: 1.36,
    Au: 1.36, Hg: 1.32, Tl: 1.45, Pb: 1.46, Bi: 1.48, Po: 1.40, At: 1.50, Rn: 1.50,
    Fr: 2.60, Ra: 2.21, Ac: 2.15, Th: 2.06, Pa: 2.00, U: 1.96, Np: 1.90, Pu: 1.87, Am: 1.80, Cm: 1.69
  };

  // ... inside component ...

  // 绘制化学键 (原子位置已经是笛卡尔坐标)
  const drawBand = (atoms: typeof structure.atoms) => {
    const list = Array.isArray(atoms) ? atoms : []
    const bandGroup = new THREE.Group();
    bandGroup.name = 'bands';

    // 优化的键长检测算法
    // 基于共价半径和 tolerance
    // d < r1 + r2 + tolerance
    const tolerance = 0.5; // Å 宽松度，允许一定的畸变

    for (let i = 0; i < list.length; i++) {
      for (let j = i + 1; j < list.length; j++) {
        // 原子位置已经是笛卡尔坐标,直接使用
        const point1 = new THREE.Vector3(...list[i].position);
        const point2 = new THREE.Vector3(...list[j].position);
        const distance = point1.distanceTo(point2);

        // 快速过滤：如果距离太大，直接跳过 (例如 > 4.0 Å)
        if (distance > 4.0) continue;
        if (distance < 0.1) continue; // 重叠原子不绘制

        const el1 = list[i].element;
        const el2 = list[j].element;
        const r1 = covalentRadii[el1] || 1.1; // 默认值 1.1
        const r2 = covalentRadii[el2] || 1.1;

        const limit = r1 + r2 + tolerance;

        if (distance < limit) {
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

  // 清理 Three.js 对象的辅助函数
  const disposeObject = (obj: THREE.Object3D) => {
    if (!obj) return;

    // 递归清理子对象
    obj.traverse((child) => {
      if (child instanceof THREE.Mesh || child instanceof THREE.Line || child instanceof THREE.LineSegments || child instanceof THREE.Sprite) {
        // 清理几何体
        if (child.geometry) {
          child.geometry.dispose();
        }

        // 清理材质
        if (child.material) {
          if (Array.isArray(child.material)) {
            child.material.forEach((material) => {
              if (material.map) material.map.dispose();
              material.dispose();
            });
          } else {
            if (child.material.map) child.material.map.dispose();
            child.material.dispose();
          }
        }
      }
    });
  };

  // 更新结构
  useEffect(() => {
    if (!sceneRef.current) {
      console.warn('Scene not initialized yet, skipping structure update');
      return;
    }

    if (!displayStructure || !Array.isArray(displayStructure.atoms) || displayStructure.atoms.length === 0) {
      console.warn('displayStructure is not ready or has no atoms, skipping structure update');
      return;
    }

    console.log('Updating structure with', displayStructure.atoms.length, 'atoms');
    const scene = sceneRef.current;

    // 移除并清理旧的原子组
    if (atomGroupRef.current) {
      disposeObject(atomGroupRef.current);
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

    console.log('Structure update complete');

  }, [displayStructure, showUnitCell, showBonds, showAxisLabels, autoRotateRef, panMode, scale, showLabels]);
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
      {/* 元素图例 */}
      <div className="absolute top-4 left-4 bg-black bg-opacity-60 p-2 rounded text-white text-xs z-10 pointer-events-none select-none">
        <h4 className="font-bold mb-1 border-b border-gray-500 pb-1">Elements</h4>
        <div className="space-y-1">
          {uniqueElements.map(el => (
            <div key={el} className="flex items-center space-x-2">
              <div
                className="w-3 h-3 rounded-full border border-gray-400"
                style={{ backgroundColor: atomColor[el.toLowerCase()] || atomColor.default }}
              />
              <span>{el}</span>
            </div>
          ))}
        </div>
      </div>

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

          <button
            onClick={() => {
              setShowLabels(!showLabels);
              setAutoRotate(false);
            }}
            className={`px-1.5 py-1 text-xs rounded transition-colors ${showLabels ? 'bg-blue-100 text-blue-600' : 'hover:bg-gray-100 text-gray-600'}`}
            title="显示/隐藏元素符号"
          >
            符号
          </button>

          {/* 晶胞类型切换 */}
          <button
            onClick={() => {
              setCellType('primitive');
              setAutoRotate(false); // 停止自动旋转
            }}
            className={`px-1.5 py-1 text-xs rounded transition-colors ${cellType === 'primitive'
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
            className={`px-1.5 py-1 text-xs rounded transition-colors ${cellType === 'conventional'
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
            className={`px-1.5 py-1 text-xs rounded transition-colors ${showDetailedInfo ? 'bg-gray-100 text-gray-600' : 'hover:bg-gray-100 text-gray-600'
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
              <span className={`px-1.5 py-0.5 rounded text-xs ${cellType === 'primitive'
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

      {/* Three.js 容器 - 完全自适应父容器大小 */}
      {isTooLarge ? (
        <div className="w-full h-full flex items-center justify-center bg-gray-50">
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
        />
      )}
    </div>
  );
};

export default StructureViewerThreeJS;

