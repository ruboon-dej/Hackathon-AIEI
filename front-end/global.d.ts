// global.d.ts
export {};

declare global {
  interface FaceApiTinyFaceDetectorOptions {
    inputSize?: number;
    scoreThreshold?: number;
  }

  interface FaceApiDetectionBox {
    x: number; y: number; width: number; height: number;
  }

  interface FaceApiDetection {
    box: FaceApiDetectionBox;
  }

  interface FaceApiNets {
    tinyFaceDetector: {
      loadFromUri: (uri: string) => Promise<void>;
    };
  }

  interface FaceApiNamespace {
    nets: FaceApiNets;
    TinyFaceDetectorOptions: new (o?: FaceApiTinyFaceDetectorOptions) => any;
    detectAllFaces: (
      input: HTMLVideoElement,
      options: any
    ) => Promise<FaceApiDetection[]>;
  }

  interface Window {
    faceapi?: FaceApiNamespace;
  }
}
