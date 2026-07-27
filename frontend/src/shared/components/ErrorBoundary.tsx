import { Component, type ErrorInfo, type ReactNode } from 'react';

import { Alert, Box, Button, Typography } from '@mui/material';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Replace with a monitoring adapter in the operations module.
    console.error('Unhandled frontend error', error, errorInfo);
  }

  render(): ReactNode {
    if (!this.state.hasError) return this.props.children;
    return (
      <Box maxWidth={600} mx="auto" mt={10} px={3}>
        <Alert severity="error">
          <Typography fontWeight={700}>The application could not render this page.</Typography>
          <Button size="small" onClick={() => window.location.reload()} sx={{ mt: 1 }}>
            Reload application
          </Button>
        </Alert>
      </Box>
    );
  }
}
