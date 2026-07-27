import type { ReactNode } from 'react';

import { Box, Typography } from '@mui/material';

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <Box py={7} textAlign="center">
      <Typography variant="h6">{title}</Typography>
      {description && <Typography mt={1} color="text.secondary">{description}</Typography>}
      {action && <Box mt={3}>{action}</Box>}
    </Box>
  );
}
