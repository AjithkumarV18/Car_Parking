import { Button } from '@mui/material';
import { Link } from 'react-router-dom';

import { EmptyState } from '@/shared/components/EmptyState';

export function NotFoundPage() {
  return (
    <EmptyState
      title="Page not found"
      description="The page you requested does not exist."
      action={<Button component={Link} to="/" variant="contained">Return home</Button>}
    />
  );
}
