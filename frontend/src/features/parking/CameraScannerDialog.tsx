import { useEffect, useRef, useState } from 'react';
import CameraAltIcon from '@mui/icons-material/CameraAlt';
import QrCodeScannerIcon from '@mui/icons-material/QrCodeScanner';
import { Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, Typography } from '@mui/material';

interface BarcodeDetectorLike {
  detect(source: ImageBitmapSource): Promise<Array<{ rawValue?: string }>>;
}

interface BarcodeDetectorConstructor {
  new (options: { formats: string[] }): BarcodeDetectorLike;
}

interface CameraScannerDialogProps {
  open: boolean;
  onClose: () => void;
  onQrDetected: (value: string) => void;
  onImageCaptured: (dataUrl: string) => void;
}

export function CameraScannerDialog({ open, onClose, onQrDetected, onImageCaptured }: CameraScannerDialogProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream>();
  const [error, setError] = useState<string>();
  const [scanning, setScanning] = useState(false);

  useEffect(() => {
    if (!open) return undefined;
    let active = true;
    async function openCamera() {
      setError(undefined);
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } }, audio: false });
        if (!active) { stream.getTracks().forEach((track) => track.stop()); return; }
        streamRef.current = stream;
        if (videoRef.current) { videoRef.current.srcObject = stream; await videoRef.current.play(); }
      } catch {
        setError('Camera access was unavailable. Allow camera access or enter the QR value manually.');
      }
    }
    void openCamera();
    return () => { active = false; streamRef.current?.getTracks().forEach((track) => track.stop()); streamRef.current = undefined; };
  }, [open]);

  async function scanQr() {
    const video = videoRef.current;
    const Detector = (window as unknown as { BarcodeDetector?: BarcodeDetectorConstructor }).BarcodeDetector;
    if (!video || !Detector) { setError('QR scanning is not supported by this browser. Use manual QR entry or capture an image.'); return; }
    setScanning(true); setError(undefined);
    try {
      const detector = new Detector({ formats: ['qr_code'] });
      const codes = await detector.detect(video);
      const value = codes[0]?.rawValue?.trim();
      if (!value) { setError('No QR code was found. Position the code inside the camera view and try again.'); return; }
      onQrDetected(value); onClose();
    } catch { setError('QR scanning failed. Try again or enter the value manually.'); } finally { setScanning(false); }
  }

  function captureImage() {
    const video = videoRef.current;
    if (!video || !video.videoWidth) { setError('The camera is still starting. Please try again.'); return; }
    const scale = Math.min(1, 1280 / Math.max(video.videoWidth, video.videoHeight));
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(video.videoWidth * scale); canvas.height = Math.round(video.videoHeight * scale);
    canvas.getContext('2d')?.drawImage(video, 0, 0);
    onImageCaptured(canvas.toDataURL('image/jpeg', 0.82)); onClose();
  }

  return <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
    <DialogTitle>Camera capture & QR scan</DialogTitle>
    <DialogContent><Stack spacing={2} pt={1}>{error && <Alert severity="warning">{error}</Alert>}
      <Box sx={{ overflow: 'hidden', borderRadius: 2, bgcolor: 'common.black', aspectRatio: '4 / 3' }}><video ref={videoRef} muted playsInline style={{ width: '100%', height: '100%', objectFit: 'cover' }} /></Box>
      <Typography variant="body2" color="text.secondary">Scan a QR code using supported browsers or capture a vehicle image from the live webcam feed.</Typography>
    </Stack></DialogContent>
    <DialogActions sx={{ p: 2 }}><Button onClick={onClose}>Cancel</Button><Button onClick={captureImage} startIcon={<CameraAltIcon />}>Capture image</Button><Button variant="contained" onClick={() => { void scanQr(); }} disabled={scanning} startIcon={<QrCodeScannerIcon />}>{scanning ? 'Scanning…' : 'Scan QR'}</Button></DialogActions>
  </Dialog>;
}
