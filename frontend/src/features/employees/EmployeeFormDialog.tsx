import { useEffect, useState, type FormEvent } from 'react';
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, Grid2, MenuItem, TextField } from '@mui/material';

import { employeeApi, type Employee, type EmployeeOptions, type EmployeePayload } from '@/features/employees/employeeApi';
import { ImageUploadField } from '@/shared/components/ImageUploadField';
import { getApiErrorMessage } from '@/shared/utils/apiError';

interface EmployeeFormDialogProps {
  open: boolean;
  employee?: Employee;
  options: EmployeeOptions;
  onClose: () => void;
  onSaved: (employee: Employee) => void;
}

const emptyPayload = (): EmployeePayload => ({
  employee_id: '', photo_url: '', name: '', gender: 'prefer_not_to_say', email: '', phone: '', designation: '', username: '', password: '', role_id: '', salary: '0.00', joining_date: new Date().toISOString().slice(0, 10), parking_location_id: null, status: 'active',
  address: { line1: '', line2: '', city: '', state: '', postal_code: '', country_code: 'IN' },
});

function normalizeIndianPhone(value: string): string {
  const normalized = value.replace(/[\s()-]/g, '');
  if (/^[6-9]\d{9}$/.test(normalized)) return `+91${normalized}`;
  if (/^0[6-9]\d{9}$/.test(normalized)) return `+91${normalized.slice(1)}`;
  if (/^91[6-9]\d{9}$/.test(normalized)) return `+${normalized}`;
  return normalized;
}

function payloadFromEmployee(employee?: Employee): EmployeePayload {
  if (!employee) return emptyPayload();
  return { employee_id: employee.employee_id, photo_url: employee.photo_url, name: employee.name, gender: employee.gender, email: employee.email, phone: employee.phone, address: employee.address, designation: employee.designation, username: employee.username, password: '', role_id: employee.role_id, salary: employee.salary, joining_date: employee.joining_date, parking_location_id: employee.parking_location_id, status: employee.status };
}

export function EmployeeFormDialog({ open, employee, options, onClose, onSaved }: EmployeeFormDialogProps) {
  const [form, setForm] = useState<EmployeePayload>(payloadFromEmployee(employee));
  const [error, setError] = useState<string>();
  const [saving, setSaving] = useState(false);
  useEffect(() => { if (open) { setForm(payloadFromEmployee(employee)); setError(undefined); } }, [open, employee]);
  const address = (key: keyof EmployeePayload['address'], value: string) => setForm((current) => ({ ...current, address: { ...current.address, [key]: value } }));

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSaving(true); setError(undefined);
    try {
      const payload: EmployeePayload = {
        ...form,
        employee_id: form.employee_id.trim().toUpperCase(), name: form.name.trim(), email: form.email.trim(), phone: normalizeIndianPhone(form.phone),
        designation: form.designation.trim(), username: form.username.trim(), photo_url: form.photo_url?.trim() || null,
        parking_location_id: form.parking_location_id || null, address: { ...form.address, line2: form.address.line2?.trim() || null },
      };
      if (!/^[A-Z0-9_-]{3,40}$/.test(payload.employee_id)) {
        throw new Error('Employee ID must contain at least 3 letters, numbers, hyphens, or underscores.');
      }
      if (!employee && !/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{12,}$/.test(payload.password ?? '')) {
        throw new Error('Password must be at least 12 characters and include upper, lower, number, and special characters.');
      }
      if (employee && !payload.password) delete payload.password;
      const response = employee ? await employeeApi.update(employee.id, payload) : await employeeApi.create(payload);
      if (!response.data) throw new Error(response.message);
      onSaved(response.data); onClose();
    } catch (requestError) { setError(getApiErrorMessage(requestError, 'Unable to save employee.')); } finally { setSaving(false); }
  }

  return <Dialog open={open} onClose={onClose} fullWidth maxWidth="md" PaperProps={{ component: 'form', onSubmit: submit }}>
    <DialogTitle>{employee ? 'Edit employee' : 'Create employee'}</DialogTitle>
    <DialogContent dividers><Grid2 container spacing={2} sx={{ pt: 0.5 }}>
      {error && <Grid2 size={12}><Alert severity="error">{error}</Alert></Grid2>}
      <Grid2 size={{ xs: 12, sm: 4 }}><TextField label="Employee ID" value={form.employee_id} onChange={(e) => setForm({ ...form, employee_id: e.target.value })} required helperText="At least 3 characters" inputProps={{ minLength: 3, pattern: '[A-Za-z0-9_-]+' }} fullWidth /></Grid2>
      <Grid2 size={{ xs: 12, sm: 8 }}><TextField label="Full name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required fullWidth /></Grid2>
      <Grid2 size={{ xs: 12, sm: 4 }}><TextField select label="Gender" value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value as EmployeePayload['gender'] })} required fullWidth><MenuItem value="male">Male</MenuItem><MenuItem value="female">Female</MenuItem><MenuItem value="non_binary">Non-binary</MenuItem><MenuItem value="prefer_not_to_say">Prefer not to say</MenuItem></TextField></Grid2>
      <Grid2 size={{ xs: 12, sm: 8 }}><ImageUploadField label="Employee photo" value={form.photo_url} onChange={(value) => setForm({ ...form, photo_url: value })} fallbackText={form.name || 'Employee'} /></Grid2>
      <Grid2 size={{ xs: 12, sm: 6 }}><TextField label="Email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required fullWidth /></Grid2>
      <Grid2 size={{ xs: 12, sm: 6 }}><TextField label="Phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="9876543210" helperText="10-digit Indian mobile accepted" required fullWidth /></Grid2>
      <Grid2 size={{ xs: 12, sm: 6 }}><TextField label="Designation" value={form.designation} onChange={(e) => setForm({ ...form, designation: e.target.value })} required fullWidth /></Grid2>
      <Grid2 size={{ xs: 12, sm: 6 }}><TextField select label="Role" value={form.role_id} onChange={(e) => setForm({ ...form, role_id: e.target.value })} required fullWidth>{options.roles.map((role) => <MenuItem key={role.id} value={role.id}>{role.name}</MenuItem>)}</TextField></Grid2>
      <Grid2 size={{ xs: 12, sm: 4 }}><TextField label="Username" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} required fullWidth /></Grid2>
      <Grid2 size={{ xs: 12, sm: 4 }}><TextField label={employee ? 'New password (optional)' : 'Password'} type="password" value={form.password ?? ''} onChange={(e) => setForm({ ...form, password: e.target.value })} required={!employee} helperText="12+ chars, upper, lower, number, special" fullWidth /></Grid2>
      <Grid2 size={{ xs: 12, sm: 4 }}><TextField label="Salary" type="number" inputProps={{ min: 0, step: '0.01' }} value={form.salary} onChange={(e) => setForm({ ...form, salary: e.target.value })} required fullWidth /></Grid2>
      <Grid2 size={{ xs: 12, sm: 4 }}><TextField label="Joining date" type="date" InputLabelProps={{ shrink: true }} value={form.joining_date} onChange={(e) => setForm({ ...form, joining_date: e.target.value })} required fullWidth /></Grid2>
      <Grid2 size={{ xs: 12, sm: 4 }}><TextField select label="Parking location" value={form.parking_location_id ?? ''} onChange={(e) => setForm({ ...form, parking_location_id: e.target.value || null })} fullWidth><MenuItem value="">Not assigned</MenuItem>{options.parking_locations.map((location) => <MenuItem key={location.id} value={location.id}>{location.name}</MenuItem>)}</TextField></Grid2>
      <Grid2 size={{ xs: 12, sm: 4 }}><TextField select label="Status" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value as EmployeePayload['status'] })} fullWidth><MenuItem value="active">Active</MenuItem><MenuItem value="on_leave">On leave</MenuItem><MenuItem value="inactive">Inactive</MenuItem></TextField></Grid2>
      <Grid2 size={12}><TextField label="Address line 1" value={form.address.line1} onChange={(e) => address('line1', e.target.value)} required fullWidth /></Grid2>
      <Grid2 size={{ xs: 12, sm: 6 }}><TextField label="City" value={form.address.city} onChange={(e) => address('city', e.target.value)} required fullWidth /></Grid2><Grid2 size={{ xs: 12, sm: 6 }}><TextField label="State" value={form.address.state} onChange={(e) => address('state', e.target.value)} required fullWidth /></Grid2>
      <Grid2 size={{ xs: 8, sm: 6 }}><TextField label="Postal code" value={form.address.postal_code} onChange={(e) => address('postal_code', e.target.value)} required fullWidth /></Grid2><Grid2 size={{ xs: 4, sm: 6 }}><TextField label="Country" value={form.address.country_code} onChange={(e) => address('country_code', e.target.value)} required fullWidth /></Grid2>
    </Grid2></DialogContent>
    <DialogActions><Button onClick={onClose}>Cancel</Button><Button type="submit" variant="contained" disabled={saving}>{saving ? 'Saving…' : 'Save employee'}</Button></DialogActions>
  </Dialog>;
}
