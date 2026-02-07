import { useCallback, useEffect, useRef, useState } from 'react';

interface VisionCapturePanelProps {
  onCapture: (base64: string, mimeType: string) => void;
  isProcessing: boolean;
  onCancel: () => void;
}

type CaptureStep = 'choose' | 'camera' | 'preview';

async function resizeAndCompress(
  file: File | Blob,
  maxDimension = 1024,
  quality = 0.7,
): Promise<{ base64: string; mimeType: string }> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const url = URL.createObjectURL(file);

    img.onload = () => {
      URL.revokeObjectURL(url);

      let { width, height } = img;
      if (width > maxDimension || height > maxDimension) {
        const ratio = Math.min(maxDimension / width, maxDimension / height);
        width = Math.round(width * ratio);
        height = Math.round(height * ratio);
      }

      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext('2d');
      if (!ctx) {
        reject(new Error('Could not get canvas context'));
        return;
      }

      ctx.drawImage(img, 0, 0, width, height);

      const dataUrl = canvas.toDataURL('image/jpeg', quality);
      const base64 = dataUrl.split(',')[1];
      resolve({ base64, mimeType: 'image/jpeg' });
    };

    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('Failed to load image'));
    };

    img.src = url;
  });
}

export function VisionCapturePanel({ onCapture, isProcessing, onCancel }: VisionCapturePanelProps) {
  const [step, setStep] = useState<CaptureStep>('choose');
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [pendingData, setPendingData] = useState<{ base64: string; mimeType: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cameraSupported, setCameraSupported] = useState(true);

  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Check camera support on mount
  useEffect(() => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraSupported(false);
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopCamera();
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [stopCamera, previewUrl]);

  const startCamera = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setStep('camera');
    } catch {
      setError('Could not access camera. Try uploading a file instead.');
      setCameraSupported(false);
    }
  }, []);

  const captureFromCamera = useCallback(async () => {
    const video = videoRef.current;
    if (!video) return;

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.drawImage(video, 0, 0);
    stopCamera();

    canvas.toBlob(
      async (blob) => {
        if (!blob) return;
        try {
          const data = await resizeAndCompress(blob);
          const url = URL.createObjectURL(blob);
          setPreviewUrl(url);
          setPendingData(data);
          setStep('preview');
        } catch {
          setError('Failed to process captured image.');
        }
      },
      'image/jpeg',
      0.9,
    );
  }, [stopCamera]);

  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setError(null);
    try {
      const data = await resizeAndCompress(file);
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
      setPendingData(data);
      setStep('preview');
    } catch {
      setError('Failed to process image file.');
    }
  }, []);

  const handleSend = useCallback(() => {
    if (pendingData) {
      onCapture(pendingData.base64, pendingData.mimeType);
    }
  }, [pendingData, onCapture]);

  const handleRetake = useCallback(() => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setPendingData(null);
    setStep('choose');
  }, [previewUrl]);

  return (
    <div className="vision-capture-panel">
      {error && <div className="vision-error" role="alert">{error}</div>}

      {step === 'choose' && (
        <div className="vision-choose">
          {cameraSupported && (
            <button
              type="button"
              className="toolbar-btn"
              onClick={startCamera}
              disabled={isProcessing}
            >
              Use Camera
            </button>
          )}
          <button
            type="button"
            className="toolbar-btn"
            onClick={() => fileInputRef.current?.click()}
            disabled={isProcessing}
          >
            Upload Image
          </button>
          <button
            type="button"
            className="toolbar-btn"
            onClick={onCancel}
            disabled={isProcessing}
          >
            Cancel
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,image/gif"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
        </div>
      )}

      {step === 'camera' && (
        <div className="vision-camera-view">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="vision-video"
          />
          <div className="extract-actions">
            <button
              type="button"
              className="toolbar-btn toolbar-btn-primary"
              onClick={captureFromCamera}
            >
              Capture
            </button>
            <button
              type="button"
              className="toolbar-btn"
              onClick={() => { stopCamera(); setStep('choose'); }}
            >
              Back
            </button>
          </div>
        </div>
      )}

      {step === 'preview' && previewUrl && (
        <div className="vision-preview">
          <img src={previewUrl} alt="Captured content" className="vision-preview-img" />
          <div className="extract-actions">
            <button
              type="button"
              className="toolbar-btn toolbar-btn-primary"
              onClick={handleSend}
              disabled={isProcessing}
            >
              {isProcessing ? 'Extracting...' : 'Extract Ideas'}
            </button>
            <button
              type="button"
              className="toolbar-btn"
              onClick={handleRetake}
              disabled={isProcessing}
            >
              Retake
            </button>
            <button
              type="button"
              className="toolbar-btn"
              onClick={onCancel}
              disabled={isProcessing}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
