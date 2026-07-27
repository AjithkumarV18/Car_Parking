import { useCallback, useEffect, useState, type Dispatch, type SetStateAction } from 'react';
import { Alert, Box, Button, Paper, Table, TableBody, TableCell, TableHead, TablePagination, TableRow, TextField, Typography } from '@mui/material';
import { Link } from 'react-router-dom';

import { PermissionGate } from '@/features/auth/PermissionGate';
import { parkingApi, type VehicleEntry, type VehicleExit } from '@/features/parking/parkingApi';
import { LoadingState } from '@/shared/components/LoadingState';
import { PageHeader } from '@/shared/components/PageHeader';
import { getApiErrorMessage } from '@/shared/utils/apiError';

interface LogFilters { page: number; limit: number; search?: string; }
const initialFilters: LogFilters = { page: 1, limit: 10 };

export function VehicleEntryLogPage() {
  const [filters, setFilters] = useState<LogFilters>(initialFilters);
  const [items, setItems] = useState<VehicleEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();
  const load = useCallback(async () => { setLoading(true); setError(undefined); try { const response = await parkingApi.entryLog(filters); setItems(response.data?.items ?? []); setTotal(response.data?.meta.total ?? 0); } catch (requestError) { setError(getApiErrorMessage(requestError, 'Unable to load open vehicle entries.')); } finally { setLoading(false); } }, [filters]);
  useEffect(() => { void load(); }, [load]);
  return <LogLayout title="Open vehicle entries" description="Vehicles currently parked in this company. Completed exits are shown only in Exit Log." filters={filters} setFilters={setFilters} total={total} loading={loading} error={error}><Table sx={{ minWidth: 950 }}><TableHead><TableRow><TableCell>Vehicle</TableCell><TableCell>Token</TableCell><TableCell>Parking no.</TableCell><TableCell>In time</TableCell><TableCell>Operator</TableCell><TableCell align="right">Action</TableCell></TableRow></TableHead><TableBody>{items.map((item) => <TableRow key={item.id}><TableCell><Typography fontWeight={700}>{item.vehicle_number}</Typography><Typography variant="body2" color="text.secondary">{item.vehicle_type}</Typography></TableCell><TableCell>{item.token_number}</TableCell><TableCell>{item.parking_number}</TableCell><TableCell>{new Date(item.entry_at).toLocaleString()}</TableCell><TableCell>{item.operator.name}<Typography variant="body2" color="text.secondary">{item.operator.employee_id ?? 'System'}</Typography></TableCell><TableCell align="right"><PermissionGate permissions={['parking_exit:show']}><Button component={Link} to={`/vehicle-exit?entryId=${encodeURIComponent(item.id)}`} variant="contained" size="small">Exit</Button></PermissionGate></TableCell></TableRow>)}</TableBody></Table></LogLayout>;
}

export function VehicleExitLogPage() {
  const [filters, setFilters] = useState<LogFilters>(initialFilters);
  const [items, setItems] = useState<VehicleExit[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();
  const load = useCallback(async () => { setLoading(true); setError(undefined); try { const response = await parkingApi.exitLog(filters); setItems(response.data?.items ?? []); setTotal(response.data?.meta.total ?? 0); } catch (requestError) { setError(getApiErrorMessage(requestError, 'Unable to load vehicle exit log.')); } finally { setLoading(false); } }, [filters]);
  useEffect(() => { void load(); }, [load]);
  return <LogLayout title="Vehicle exit log" description="Latest completed vehicle check-outs and payments." filters={filters} setFilters={setFilters} total={total} loading={loading} error={error}><Table sx={{ minWidth: 960 }}><TableHead><TableRow><TableCell>Vehicle</TableCell><TableCell>Token</TableCell><TableCell>In time</TableCell><TableCell>Out time</TableCell><TableCell>Total</TableCell><TableCell>Payment</TableCell></TableRow></TableHead><TableBody>{items.map((item) => <TableRow key={item.id}><TableCell><Typography fontWeight={700}>{item.entry.vehicle_number}</Typography><Typography variant="body2" color="text.secondary">{item.entry.vehicle_type}</Typography></TableCell><TableCell>{item.entry.token_number}</TableCell><TableCell>{new Date(item.entry.entry_at).toLocaleString()}</TableCell><TableCell>{new Date(item.exit_at).toLocaleString()}</TableCell><TableCell>₹{item.total_amount}</TableCell><TableCell>{item.payment_method?.toUpperCase() ?? 'Advance'}</TableCell></TableRow>)}</TableBody></Table></LogLayout>;
}

function LogLayout({ title, description, filters, setFilters, total, loading, error, children }: { title: string; description: string; filters: LogFilters; setFilters: Dispatch<SetStateAction<LogFilters>>; total: number; loading: boolean; error?: string; children: React.ReactNode }) {
  return <><PageHeader title={title} description={description} />{error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}<Paper variant="outlined" sx={{ p: 2, mb: 2 }}><TextField size="small" label="Search vehicle, token, or parking number" value={filters.search ?? ''} onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value || undefined, page: 1 }))} fullWidth /></Paper><Paper variant="outlined" sx={{ overflowX: 'auto' }}>{loading ? <LoadingState label="Loading log…" /> : <><Box>{children}</Box><TablePagination component="div" count={total} page={filters.page - 1} rowsPerPage={filters.limit} rowsPerPageOptions={[10, 25, 50, 100]} onPageChange={(_, page) => setFilters((current) => ({ ...current, page: page + 1 }))} onRowsPerPageChange={(event) => setFilters((current) => ({ ...current, page: 1, limit: Number(event.target.value) }))} /></>}</Paper></>;
}
