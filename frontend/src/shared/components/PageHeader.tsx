import type { ReactNode } from 'react';

import { Box, Typography } from '@mui/material';

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: ReactNode;
}

export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <Box display="flex" gap={2} justifyContent="space-between" alignItems="flex-start" mb={3}>
      <Box>
        <Typography variant="h4" component="h1">{title}</Typography>
        {description && <Typography mt={0.5} color="text.secondary">{description}</Typography>}
      </Box>
      {actions && <Box flexShrink={0}>{actions}</Box>}
    </Box>
  );
}
