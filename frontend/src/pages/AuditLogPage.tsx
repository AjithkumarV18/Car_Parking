import { useCallback, useEffect, useState } from 'react';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import HistoryIcon from '@mui/icons-material/History';
import RefreshIcon from '@mui/icons-material/Refresh';
import VisibilityOutlinedIcon from '@mui/icons-material/VisibilityOutlined';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import { Alert, Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, Divider, Grid2, IconButton, List, ListItem, ListItemAvatar, ListItemText, MenuItem, Paper, Stack, Table, TableBody, TableCell, TableHead, TablePagination, TableRow, TextField, Typography } from '@mui/material';

import { PermissionGate } from '@/features/auth/PermissionGate';
import { auditApi, type AuditFilters, type AuditLevel, type AuditLog, type AuditTimelineItem } from '@/features/audit/auditApi';
import { useNotification } from '@/features/notifications/useNotification';
import { LoadingState } from '@/shared/components/LoadingState';
import { PageHeader } from '@/shared/components/PageHeader';
import { getApiErrorMessage } from '@/shared/utils/apiError';

const modules = ['auth', 'company', 'role', 'employee', 'rate', 'parking_entry', 'parking_exit'] as const;

function today(): string { return new Date().toISOString().slice(0, 10); }
function thirtyDaysAgo(): string { const value = new Date(); value.setDate(value.getDate() - 29); return value.toISOString().slice(0, 10); }

export function AuditLogPage() {
  const [filters, setFilters] = useState<AuditFilters>({ date_from: thirtyDaysAgo(), date_to: today(), page: 1, limit: 25 });
  const [logs, setLogs] = useState<AuditTimelineItem[]>([]);
  const [timeline, setTimeline] = useState<AuditTimelineItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();
  const [selected, setSelected] = useState<AuditLog>();
  const [detailsLoading, setDetailsLoading] = useState(false);
  const notifications = useNotification();

  const load = useCallback(async (showToast = false) => {
    setLoading(true); setError(undefined);
    const timelineFilters = { date_from: filters.date_from, date_to: filters.date_to, module: filters.module, action: filters.action, level: filters.level, user_id: filters.user_id, search: filters.search };
    try {
      const [listResponse, timelineResponse] = await Promise.all([auditApi.list(filters), auditApi.timeline(timelineFilters)]);
      const loadedTotal = listResponse.data?.meta.total ?? 0;
      setLogs(listResponse.data?.items ?? []); setTotal(loadedTotal); setTimeline(timelineResponse.data ?? []);
      if (showToast) { if (loadedTotal) notifications.success('Audit logs refreshed.'); else notifications.warning('No audit activity matches the selected filters.'); }
    } catch (requestError) { const message = getApiErrorMessage(requestError, 'Unable to load audit logs.'); setError(message); notifications.error(message); }
    finally { setLoading(false); }
  }, [filters, notifications]);
  useEffect(() => { void load(); }, [load]);

  function setFilter<K extends keyof AuditFilters>(key: K, value: AuditFilters[K]) { setFilters((current) => ({ ...current, [key]: value || undefined, page: 1 })); }
  async function viewDetails(id: string) {
    setDetailsLoading(true);
    try { const response = await auditApi.get(id); if (!response.data) throw new Error(response.message); setSelected(response.data); }
    catch (requestError) { notifications.error(getApiErrorMessage(requestError, 'Unable to load audit log details.')); }
    finally { setDetailsLoading(false); }
  }

  return <>
    <PageHeader title="Audit logs" description="Trace user activity, client IPs, request outcomes, and before/after changes for the selected company." actions={<Button variant="outlined" startIcon={<RefreshIcon />} onClick={() => { void load(true); }} disabled={loading}>Refresh</Button>} />
    {error && <Alert severity="error" action={<Button color="inherit" size="small" onClick={() => { void load(); }}>Retry</Button>} sx={{ mb: 2 }}>{error}</Alert>}
    <FilterBar filters={filters} onChange={setFilter} />
    <Grid2 container spacing={3}>
      <Grid2 size={{ xs: 12, lg: 8 }}><Paper variant="outlined" sx={{ overflowX: 'auto' }}>{loading ? <LoadingState label="Loading audit activity…" /> : <><Table sx={{ minWidth: 900 }}><TableHead><TableRow><TableCell>When</TableCell><TableCell>User / IP</TableCell><TableCell>Module</TableCell><TableCell>Action</TableCell><TableCell>Outcome</TableCell><TableCell>Message</TableCell><TableCell align="right">Details</TableCell></TableRow></TableHead><TableBody>{logs.map((log) => <TableRow key={log.id} hover><TableCell><Typography variant="body2" fontWeight={700}>{log.date}</Typography><Typography variant="caption" color="text.secondary">{log.time}</Typography></TableCell><TableCell><Typography variant="body2" fontWeight={600}>{log.actor.name}</Typography><Typography variant="caption" color="text.secondary">{log.ip_address || 'IP unavailable'}</Typography></TableCell><TableCell><Chip label={log.module.replaceAll('_', ' ')} size="small" variant="outlined" /></TableCell><TableCell sx={{ textTransform: 'capitalize' }}>{log.action.replaceAll('_', ' ')}</TableCell><TableCell><LevelChip level={log.level} /></TableCell><TableCell sx={{ maxWidth: 240 }}><Typography variant="body2" noWrap title={log.message}>{log.message}</Typography></TableCell><TableCell align="right"><PermissionGate permissions={['audit:details']}><IconButton aria-label="View audit details" onClick={() => { void viewDetails(log.id); }} disabled={detailsLoading}><VisibilityOutlinedIcon /></IconButton></PermissionGate></TableCell></TableRow>)}</TableBody></Table><TablePagination component="div" count={total} page={(filters.page ?? 1) - 1} rowsPerPage={filters.limit ?? 25} onPageChange={(_, page) => setFilters((current) => ({ ...current, page: page + 1 }))} onRowsPerPageChange={(event) => setFilters((current) => ({ ...current, limit: Number(event.target.value), page: 1 }))} rowsPerPageOptions={[10, 25, 50, 100]} /></>}</Paper></Grid2>
      <Grid2 size={{ xs: 12, lg: 4 }}><Paper variant="outlined" sx={{ p: 2, height: '100%' }}><Stack direction="row" spacing={1} alignItems="center" mb={1}><HistoryIcon color="primary" /><Typography variant="h6" fontWeight={800}>Activity timeline</Typography></Stack><Typography variant="body2" color="text.secondary" mb={1.5}>Latest matching activity, newest first.</Typography>{loading ? <LoadingState label="Loading timeline…" /> : <ActivityTimeline items={timeline} />}</Paper></Grid2>
    </Grid2>
    <AuditDetailDialog log={selected} onClose={() => setSelected(undefined)} />
  </>;
}

function FilterBar({ filters, onChange }: { filters: AuditFilters; onChange: <K extends keyof AuditFilters>(key: K, value: AuditFilters[K]) => void }) {
  return <Paper variant="outlined" sx={{ p: 2, mb: 3 }}><Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5}>
    <TextField size="small" type="date" label="From date" value={filters.date_from ?? ''} onChange={(event) => onChange('date_from', event.target.value)} InputLabelProps={{ shrink: true }} />
    <TextField size="small" type="date" label="To date" value={filters.date_to ?? ''} onChange={(event) => onChange('date_to', event.target.value)} InputLabelProps={{ shrink: true }} />
    <TextField size="small" label="Search activity or IP" value={filters.search ?? ''} onChange={(event) => onChange('search', event.target.value)} sx={{ minWidth: { md: 220 } }} />
    <TextField select size="small" label="Module" value={filters.module ?? ''} onChange={(event) => onChange('module', event.target.value)} sx={{ minWidth: 155 }}><MenuItem value="">All modules</MenuItem>{modules.map((module) => <MenuItem key={module} value={module}>{module.replaceAll('_', ' ')}</MenuItem>)}</TextField>
    <TextField select size="small" label="Level" value={filters.level ?? ''} onChange={(event) => onChange('level', event.target.value as AuditLevel)} sx={{ minWidth: 135 }}><MenuItem value="">All levels</MenuItem><MenuItem value="success">Success</MenuItem><MenuItem value="warning">Warning</MenuItem><MenuItem value="error">Error</MenuItem></TextField>
  </Stack></Paper>;
}

function LevelChip({ level }: { level: AuditLevel }) {
  const config = { success: { label: 'Success', color: 'success' as const }, warning: { label: 'Warning', color: 'warning' as const }, error: { label: 'Error', color: 'error' as const } }[level];
  return <Chip label={config.label} color={config.color} size="small" />;
}

function ActivityTimeline({ items }: { items: AuditTimelineItem[] }) {
  if (!items.length) return <Box py={4} textAlign="center"><Typography fontWeight={700}>No activity found</Typography><Typography variant="body2" color="text.secondary" mt={0.5}>Matching actions will appear here.</Typography></Box>;
  const icon = (level: AuditLevel) => level === 'success' ? <CheckCircleOutlineIcon color="success" fontSize="small" /> : level === 'warning' ? <WarningAmberIcon color="warning" fontSize="small" /> : <ErrorOutlineIcon color="error" fontSize="small" />;
  return <List disablePadding>{items.map((item, index) => <ListItem key={item.id} alignItems="flex-start" disableGutters divider={index < items.length - 1}><ListItemAvatar sx={{ minWidth: 36 }}>{icon(item.level)}</ListItemAvatar><ListItemText primary={<Typography variant="body2" fontWeight={700}>{item.message}</Typography>} secondary={<><Typography component="span" variant="caption" display="block">{item.actor.name} · {item.module.replaceAll('_', ' ')} · {item.ip_address || 'IP unavailable'}</Typography><Typography component="span" variant="caption" color="text.secondary">{item.date} {item.time}</Typography></>} /></ListItem>)}</List>;
}

function AuditDetailDialog({ log, onClose }: { log?: AuditLog; onClose: () => void }) {
  return <Dialog open={Boolean(log)} onClose={onClose} fullWidth maxWidth="md"><DialogTitle>Audit log details</DialogTitle><DialogContent dividers>{log && <Stack spacing={2}><Grid2 container spacing={1.5}><Grid2 size={{ xs: 12, sm: 6 }}><Typography variant="body2" color="text.secondary">User</Typography><Typography fontWeight={700}>{log.actor.name}</Typography></Grid2><Grid2 size={{ xs: 12, sm: 6 }}><Typography variant="body2" color="text.secondary">IP address</Typography><Typography fontWeight={700}>{log.ip_address || 'Unavailable'}</Typography></Grid2><Grid2 size={{ xs: 12, sm: 6 }}><Typography variant="body2" color="text.secondary">Activity</Typography><Typography fontWeight={700}>{log.module.replaceAll('_', ' ')} · {log.action.replaceAll('_', ' ')}</Typography></Grid2><Grid2 size={{ xs: 12, sm: 6 }}><Typography variant="body2" color="text.secondary">When</Typography><Typography fontWeight={700}>{log.date} {log.time}</Typography></Grid2></Grid2><Divider /><ValueBlock title="Old value" value={log.old_value} /><ValueBlock title="New value" value={log.new_value} /><Typography variant="caption" color="text.secondary">Request ID: {log.request_id || 'Unavailable'}</Typography></Stack>}</DialogContent><DialogActions><Button onClick={onClose}>Close</Button></DialogActions></Dialog>;
}

function ValueBlock({ title, value }: { title: string; value: AuditLog['old_value'] }) {
  return <Box><Typography fontWeight={800} mb={0.75}>{title}</Typography><Box component="pre" sx={{ m: 0, p: 1.5, maxHeight: 260, overflow: 'auto', borderRadius: 1, bgcolor: 'grey.100', fontSize: '0.75rem', whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{value === null ? 'No value recorded.' : JSON.stringify(value, null, 2)}</Box></Box>;
}
