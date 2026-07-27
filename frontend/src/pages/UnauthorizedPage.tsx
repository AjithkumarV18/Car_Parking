import { Button } from '@mui/material';
import { Link } from 'react-router-dom';

import { EmptyState } from '@/shared/components/EmptyState';

export function UnauthorizedPage() {
  return (
    <EmptyState
      title="Access unavailable"
      description="Sign in with an account that has access to this area."
      action={<Button component={Link} to="/" variant="contained">Return home</Button>}
    />
  );
}
