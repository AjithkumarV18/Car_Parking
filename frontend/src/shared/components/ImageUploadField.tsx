import { useState, type ChangeEvent } from 'react';
import UploadOutlinedIcon from '@mui/icons-material/UploadOutlined';
import { Alert, Avatar, Box, Button, Stack, Typography } from '@mui/material';

const acceptedTypes = ['image/jpeg', 'image/png', 'image/webp'];
const maxBytes = 2 * 1024 * 1024;

interface ImageUploadFieldProps {
  label: string;
  value?: string | null;
  onChange: (value: string | null) => void;
  shape?: 'circle' | 'rounded';
  fallbackText?: string;
}

function readImage(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => typeof reader.result === 'string' ? resolve(reader.result) : reject(new Error('Unable to read image.'));
    reader.onerror = () => reject(new Error('Unable to read image.'));
    reader.readAsDataURL(file);
  });
}

export function ImageUploadField({ label, value, onChange, shape = 'circle', fallbackText = 'Image' }: ImageUploadFieldProps) {
  const [error, setError] = useState<string>();

  async function selectFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    if (!acceptedTypes.includes(file.type)) {
      setError('Choose a JPEG, PNG, or WebP image.');
      return;
    }
    if (file.size > maxBytes) {
      setError('Image must be 2 MB or smaller.');
      return;
    }
    try {
      setError(undefined);
      onChange(await readImage(file));
    } catch {
      setError('Unable to read the selected image.');
    }
  }

  return <Stack spacing={1}>
    <Typography variant="subtitle2">{label}</Typography>
    <Stack direction="row" spacing={1.5} alignItems="center">
      {shape === 'circle' ? <Avatar src={value ?? undefined} sx={{ width: 64, height: 64 }}>{fallbackText.slice(0, 1)}</Avatar> : <Box component="img" src={value ?? undefined} alt="" sx={{ width: 112, height: 64, borderRadius: 1, border: 1, borderColor: 'divider', objectFit: 'contain', p: 0.5, display: value ? 'block' : 'none' }} />}
      {shape === 'rounded' && !value && <Box sx={{ width: 112, height: 64, borderRadius: 1, border: 1, borderColor: 'divider', display: 'grid', placeItems: 'center' }}><Typography color="text.secondary" variant="body2">{fallbackText}</Typography></Box>}
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
        <Button component="label" variant="outlined" size="small" startIcon={<UploadOutlinedIcon />}>Upload<input hidden type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => { void selectFile(event); }} /></Button>
        {value && <Button size="small" color="inherit" onClick={() => onChange(null)}>Remove</Button>}
      </Stack>
    </Stack>
    <Typography variant="caption" color="text.secondary">JPEG, PNG, or WebP up to 2 MB.</Typography>
    {error && <Alert severity="error" sx={{ py: 0 }}>{error}</Alert>}
  </Stack>;
}
