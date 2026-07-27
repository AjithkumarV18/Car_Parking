import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import { Alert, Button, Card, CardContent, Chip, Grid2, Stack, Typography } from '@mui/material';
import { Link } from 'react-router-dom';

import { PageHeader } from '@/shared/components/PageHeader';

const CAPABILITIES = [
  'React + TypeScript shell',
  'Router and Material UI theme',
  'Typed Axios API client',
  'JWT-aware client session',
  'FastAPI Clean Architecture',
  'MongoDB repository boundary',
  'JWT authorization dependencies',
  'Standard response and pagination models',
  'Structured logging and error handling',
  'Docker Compose deployment',
];

export function FoundationPage() {
  return (
    <>
      <PageHeader
        title="Platform Foundation"
        description="Commercial vehicle parking platform infrastructure is ready for feature modules."
      />
      <Alert icon={<CheckCircleOutlineIcon />} severity="success" sx={{ mb: 3 }}>
        Authentication is now available; parking business modules are not included yet.
      </Alert>
      <Stack direction="row" spacing={1} mb={3}><Button component={Link} to="/login" variant="contained">Sign in</Button><Button component={Link} to="/register">Register</Button></Stack>
      <Grid2 container spacing={2}>
        {CAPABILITIES.map((capability) => (
          <Grid2 key={capability} size={{ xs: 12, sm: 6 }}>
            <Card variant="outlined" sx={{ height: '100%' }}>
              <CardContent>
                <Stack direction="row" spacing={1} alignItems="center">
                  <CheckCircleOutlineIcon color="primary" fontSize="small" />
                  <Typography fontWeight={600}>{capability}</Typography>
                </Stack>
              </CardContent>
            </Card>
          </Grid2>
        ))}
      </Grid2>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap mt={4}>
        <Chip label="Foundation only" color="primary" />
        <Chip label="API versioned" variant="outlined" />
        <Chip label="Swagger enabled" variant="outlined" />
      </Stack>
    </>
  );
}
