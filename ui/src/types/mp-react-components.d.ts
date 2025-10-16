/**
 * Type declarations for @materialsproject/mp-react-components
 * 
 * This file provides TypeScript type definitions for the Materials Project
 * React components library.
 */

declare module '@materialsproject/mp-react-components' {
  import { FC, ReactNode } from 'react';

  /**
   * Scene data format for CrystalToolkitScene
   */
  export interface SceneData {
    name?: string;
    contents: Array<SceneObject>;
    origin?: [number, number, number];
    visible?: boolean;
  }

  /**
   * Base interface for scene objects
   */
  interface SceneObject {
    type: string;
    [key: string]: any;
  }

  /**
   * Sphere object in the scene
   */
  export interface SphereObject extends SceneObject {
    type: 'spheres';
    positions: Array<[number, number, number]>;
    radius: number;
    color: string;
    phong?: number;
    tooltip?: string;
  }

  /**
   * Cylinder object in the scene
   */
  export interface CylinderObject extends SceneObject {
    type: 'cylinders';
    positionPairs: Array<[[number, number, number], [number, number, number]]>;
    radius: number;
    color: string;
  }

  /**
   * Settings for CrystalToolkitScene
   */
  export interface CrystalToolkitSettings {
    antialias?: boolean;
    renderer?: 'webgl' | 'svg';
    transparentBackground?: boolean;
    background?: string;
    sphereSegments?: number;
    cylinderSegments?: number;
    staticScene?: boolean;
    defaultZoom?: number;
    zoomToFit2D?: boolean;
    extractAxis?: boolean;
    [key: string]: any;
  }

  /**
   * Props for CrystalToolkitScene component
   */
  export interface CrystalToolkitSceneProps {
    data: SceneData;
    settings?: CrystalToolkitSettings;
    sceneSize?: string | number;
    showControls?: boolean;
    showExpandButton?: boolean;
    showImageButton?: boolean;
    showExportButton?: boolean;
    showPositionButton?: boolean;
    [key: string]: any;
  }

  /**
   * Main crystal structure visualization component
   */
  export const CrystalToolkitScene: FC<CrystalToolkitSceneProps>;

  /**
   * Animation scene component
   */
  export interface CrystalToolkitAnimationSceneProps extends CrystalToolkitSceneProps {
    animationData?: any;
    animationStyle?: string;
  }

  export const CrystalToolkitAnimationScene: FC<CrystalToolkitAnimationSceneProps>;

  /**
   * Camera context provider
   */
  export interface CameraContextProviderProps {
    children: ReactNode;
  }

  export const CameraContextProvider: FC<CameraContextProviderProps>;

  /**
   * Pymatgen structure format
   */
  export interface PymatgenStructure {
    '@module': string;
    '@class': string;
    charge?: number;
    lattice: {
      matrix: number[][];
      a: number;
      b: number;
      c: number;
      alpha: number;
      beta: number;
      gamma: number;
      volume: number;
    };
    sites: Array<{
      species: Array<{
        element: string;
        occu: number;
      }>;
      abc: [number, number, number];
      xyz: [number, number, number];
      label: string;
      properties?: any;
    }>;
  }

  /**
   * Base scene component - accepts pymatgen structure
   */
  export interface SceneProps {
    data: PymatgenStructure | any;
    settings?: any;
    sceneSize?: string | number;
    [key: string]: any;
  }

  export const Scene: FC<SceneProps>;
}

