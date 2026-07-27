import { useCallback, useEffect, useMemo, useState } from 'react';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import DownloadIcon from '@mui/icons-material/Download';
import EditOutlinedIcon from '@mui/icons-material/EditOutlined';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import PrintIcon from '@mui/icons-material/Print';
import VisibilityOutlinedIcon from '@mui/icons-material/VisibilityOutlined';
import { Alert, Avatar, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, IconButton, MenuItem, Paper, Stack, Table, TableBody, TableCell, TableHead, TablePagination, TableRow, TextField, Typography } from '@mui/material';

import { EmployeeFormDialog } from '@/features/employees/EmployeeFormDialog';
import { employeeApi, type Employee, type EmployeeFilters, type EmployeeOptions } from '@/features/employees/employeeApi';
import { PermissionGate } from '@/features/auth/PermissionGate';
import { LoadingState } from '@/shared/components/LoadingState';
import { PageHeader } from '@/shared/components/PageHeader';
import { getApiErrorMessage } from '@/shared/utils/apiError';

const initialFilters: EmployeeFilters = { page: 1, limit: 10, sort_by: 'name' };

export function EmployeeManagementPage() {
  const [filters, setFilters] = useState<EmployeeFilters>(initialFilters);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [total, setTotal] = useState(0);
  const [options, setOptions] = useState<EmployeeOptions>({ roles: [], parking_locations: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Employee>();
  const [details, setDetails] = useState<Employee>();

  const load = useCallback(async () => {
    setLoading(true); setError(undefined);
    try {
      const response = await employeeApi.list(filters);
      setEmployees(response.data?.items ?? []); setTotal(response.data?.meta.total ?? 0);
    } catch (requestError) { setError(getApiErrorMessage(requestError, 'Unable to load employees.')); }
    finally { setLoading(false); }
  }, [filters]);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => { void employeeApi.options().then((response) => setOptions(response.data ?? { roles: [], parking_locations: [] })).catch((requestError) => setError(getApiErrorMessage(requestError, 'Unable to load employee options.'))); }, []);

  const exportFilters = useMemo(() => ({
    search: filters.search,
    status: filters.status,
    gender: filters.gender,
    role_id: filters.role_id,
    parking_location_id: filters.parking_location_id,
    sort_by: filters.sort_by,
    sort_order: filters.sort_order,
  }), [filters]);
  function saved(employee: Employee) { setEmployees((current) => current.some((item) => item.id === employee.id) ? current.map((item) => item.id === employee.id ? employee : item) : [employee, ...current]); }
  async function remove(employee: Employee) { if (!window.confirm(`Deactivate ${employee.name}? Their login will be disabled.`)) return; try { await employeeApi.remove(employee.id); await load(); } catch (requestError) { setError(getApiErrorMessage(requestError, 'Unable to deactivate employee.')); } }
  async function exportFile(format: 'excel' | 'pdf') { try { await employeeApi.download(format, exportFilters); } catch (requestError) { setError(getApiErrorMessage(requestError, `Unable to export ${format}.`)); } }
  function setFilter<K extends keyof EmployeeFilters>(key: K, value: EmployeeFilters[K]) { setFilters((current) => ({ ...current, [key]: value, page: 1 })); }

  return <>
    <PageHeader title="Employee management" description="Tenant workforce directory, credentials, roles, and parking-location assignments." actions={<PermissionGate permissions={['employee:save']}><Button variant="contained" startIcon={<AddIcon />} onClick={() => setCreating(true)}>Add employee</Button></PermissionGate>} />
    {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
    <Paper variant="outlined" sx={{ p: 2, mb: 2 }}><Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5} alignItems={{ md: 'center' }}>
      <TextField size="small" label="Search" value={filters.search ?? ''} onChange={(e) => setFilter('search', e.target.value || undefined)} sx={{ minWidth: { md: 220 } }} />
      <TextField select size="small" label="Status" value={filters.status ?? ''} onChange={(e) => setFilter('status', (e.target.value || undefined) as EmployeeFilters['status'])} sx={{ minWidth: 140 }}><MenuItem value="">All statuses</MenuItem><MenuItem value="active">Active</MenuItem><MenuItem value="on_leave">On leave</MenuItem><MenuItem value="inactive">Inactive</MenuItem></TextField>
      <TextField select size="small" label="Role" value={filters.role_id ?? ''} onChange={(e) => setFilter('role_id', e.target.value || undefined)} sx={{ minWidth: 160 }}><MenuItem value="">All roles</MenuItem>{options.roles.map((role) => <MenuItem key={role.id} value={role.id}>{role.name}</MenuItem>)}</TextField>
      <TextField select size="small" label="Location" value={filters.parking_location_id ?? ''} onChange={(e) => setFilter('parking_location_id', e.target.value || undefined)} sx={{ minWidth: 180 }}><MenuItem value="">All locations</MenuItem>{options.parking_locations.map((location) => <MenuItem key={location.id} value={location.id}>{location.name}</MenuItem>)}</TextField>
      <TextField select size="small" label="Sort" value={filters.sort_by} onChange={(e) => setFilter('sort_by', e.target.value as EmployeeFilters['sort_by'])} sx={{ minWidth: 150 }}><MenuItem value="name">Name</MenuItem><MenuItem value="employee_id">Employee ID</MenuItem><MenuItem value="joining_date">Joining date</MenuItem><MenuItem value="salary">Salary</MenuItem><MenuItem value="designation">Designation</MenuItem></TextField>
      <Box flexGrow={1} /><PermissionGate permissions={['employee:details']}><Button size="small" startIcon={<DownloadIcon />} onClick={() => { void exportFile('excel'); }}>Excel</Button><Button size="small" startIcon={<PictureAsPdfIcon />} onClick={() => { void exportFile('pdf'); }}>PDF</Button></PermissionGate><Button size="small" startIcon={<PrintIcon />} onClick={() => window.print()}>Print</Button>
    </Stack></Paper>
    <Paper variant="outlined" className="employee-print-table" sx={{ overflowX: 'auto' }}>{loading ? <LoadingState label="Loading employees…" /> : <><Table sx={{ minWidth: 900 }}><TableHead><TableRow><TableCell>Employee</TableCell><TableCell>Designation</TableCell><TableCell>Role</TableCell><TableCell>Location</TableCell><TableCell>Joining</TableCell><TableCell>Status</TableCell><TableCell align="right">Actions</TableCell></TableRow></TableHead><TableBody>{employees.map((employee) => <TableRow key={employee.id}><TableCell><Stack direction="row" spacing={1} alignItems="center"><Avatar src={employee.photo_url ?? undefined}>{employee.name.slice(0, 1)}</Avatar><Box><Typography fontWeight={600}>{employee.name}</Typography><Typography variant="body2" color="text.secondary">{employee.employee_id} · {employee.email}</Typography></Box></Stack></TableCell><TableCell>{employee.designation}</TableCell><TableCell>{employee.role_name}</TableCell><TableCell>{employee.parking_location_name || 'Unassigned'}</TableCell><TableCell>{employee.joining_date}</TableCell><TableCell sx={{ textTransform: 'capitalize' }}>{employee.status.replace('_', ' ')}</TableCell><TableCell align="right"><PermissionGate permissions={['employee:details']}><IconButton aria-label="View employee" onClick={() => setDetails(employee)}><VisibilityOutlinedIcon /></IconButton></PermissionGate><PermissionGate permissions={['employee:edit']}><IconButton aria-label="Edit employee" onClick={() => setEditing(employee)}><EditOutlinedIcon /></IconButton></PermissionGate><PermissionGate permissions={['employee:delete']}><IconButton aria-label="Deactivate employee" color="error" onClick={() => { void remove(employee); }}><DeleteOutlineIcon /></IconButton></PermissionGate></TableCell></TableRow>)}</TableBody></Table><TablePagination component="div" count={total} page={(filters.page ?? 1) - 1} onPageChange={(_, page) => setFilters((current) => ({ ...current, page: page + 1 }))} rowsPerPage={filters.limit ?? 10} onRowsPerPageChange={(event) => setFilters((current) => ({ ...current, limit: Number(event.target.value), page: 1 }))} rowsPerPageOptions={[10, 25, 50, 100]} /></>}</Paper>
    <EmployeeFormDialog open={creating || Boolean(editing)} employee={editing} options={options} onClose={() => { setCreating(false); setEditing(undefined); }} onSaved={saved} />
    <Dialog open={Boolean(details)} onClose={() => setDetails(undefined)} fullWidth maxWidth="sm"><DialogTitle>{details?.name}</DialogTitle><DialogContent><Stack spacing={1}><Typography><strong>Employee ID:</strong> {details?.employee_id}</Typography><Typography><strong>Designation:</strong> {details?.designation}</Typography><Typography><strong>Role:</strong> {details?.role_name}</Typography><Typography><strong>Phone:</strong> {details?.phone}</Typography><Typography><strong>Salary:</strong> {details?.salary}</Typography><Typography><strong>Address:</strong> {details?.address.line1}, {details?.address.city}, {details?.address.state}</Typography></Stack></DialogContent><DialogActions><Button onClick={() => setDetails(undefined)}>Close</Button></DialogActions></Dialog>
  </>;
}
