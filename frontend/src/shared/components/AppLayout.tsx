import { useMemo, useState, type ReactNode } from 'react';
import AccountTreeOutlinedIcon from '@mui/icons-material/AccountTreeOutlined';
import AdminPanelSettingsOutlinedIcon from '@mui/icons-material/AdminPanelSettingsOutlined';
import ApartmentOutlinedIcon from '@mui/icons-material/ApartmentOutlined';
import AssessmentOutlinedIcon from '@mui/icons-material/AssessmentOutlined';
import CardMembershipOutlinedIcon from '@mui/icons-material/CardMembershipOutlined';
import DarkModeIcon from '@mui/icons-material/DarkMode';
import EventSeatOutlinedIcon from '@mui/icons-material/EventSeatOutlined';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import GroupsOutlinedIcon from '@mui/icons-material/GroupsOutlined';
import HistoryOutlinedIcon from '@mui/icons-material/HistoryOutlined';
import LightModeIcon from '@mui/icons-material/LightMode';
import LoginIcon from '@mui/icons-material/Login';
import LogoutIcon from '@mui/icons-material/Logout';
import MenuIcon from '@mui/icons-material/Menu';
import PaymentsOutlinedIcon from '@mui/icons-material/PaymentsOutlined';
import ReceiptLongOutlinedIcon from '@mui/icons-material/ReceiptLongOutlined';
import SettingsBackupRestoreOutlinedIcon from '@mui/icons-material/SettingsBackupRestoreOutlined';
import SettingsOutlinedIcon from '@mui/icons-material/SettingsOutlined';
import SpaceDashboardOutlinedIcon from '@mui/icons-material/SpaceDashboardOutlined';
import TranslateOutlinedIcon from '@mui/icons-material/TranslateOutlined';
import { alpha } from '@mui/material/styles';
import { AppBar, Avatar, Badge, Box, Collapse, Container, Divider, Drawer, IconButton, List, ListItemButton, ListItemIcon, ListItemText, MenuItem, Select, Stack, Toolbar, Tooltip, Typography } from '@mui/material';
import { Link, Outlet, useLocation } from 'react-router-dom';

import { env } from '@/config/env';
import { useAuth } from '@/features/auth/useAuth';
import { usePreferences } from '@/features/preferences/usePreferences';
import { usePublicCompany } from '@/features/setup/usePublicCompany';

const drawerWidth = 292;

interface TreeItem {
  label: string;
  to: string;
  permission?: string;
  superAdmin?: boolean;
  icon: ReactNode;
}

interface TreeGroup {
  key: string;
  label: string;
  icon: ReactNode;
  items: TreeItem[];
}

export function AppLayout() {
  const { user, signOut } = useAuth();
  const { language, mode, setLanguage, toggleMode, t } = usePreferences();
  const { company: publicCompany } = usePublicCompany();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({ operations: true, administration: true, insights: true, system: true });
  const companyName = user?.companyName || publicCompany?.company_name || env.appName;
  const companyLogo = user?.companyLogoUrl || publicCompany?.logo_url;
  const userName = user?.displayName || user?.username || t('User');
  const userRole = (user?.isSuperAdmin ? t('Super Admin') : user?.roles[0]?.replaceAll('_', ' ') || t('Employee')).replace(/\b\w/g, (letter) => letter.toUpperCase());

  const groups = useMemo<TreeGroup[]>(() => [
    {
      key: 'operations', label: t('Operations'), icon: <EventSeatOutlinedIcon />, items: [
        { label: t('Dashboard'), to: '/app', permission: 'dashboard:show', icon: <SpaceDashboardOutlinedIcon /> },
        { label: t('Entry'), to: '/vehicle-entry', permission: 'parking_entry:show', icon: <LoginIcon /> },
        { label: t('Entry log'), to: '/vehicle-entry-log', permission: 'parking_entry:show', icon: <ReceiptLongOutlinedIcon /> },
        { label: t('Exit'), to: '/vehicle-exit', permission: 'parking_exit:show', icon: <LogoutIcon /> },
        { label: t('Exit log'), to: '/vehicle-exit-log', permission: 'parking_exit:show', icon: <HistoryOutlinedIcon /> },
        { label: t('Parking+'), to: '/advanced-parking', permission: 'advanced:show', icon: <EventSeatOutlinedIcon /> },
        { label: t('Monthly passes'), to: '/monthly-passes', permission: 'advanced:show', icon: <CardMembershipOutlinedIcon /> },
      ],
    },
    {
      key: 'administration', label: t('Administration'), icon: <AdminPanelSettingsOutlinedIcon />, items: [
        { label: t('Companies'), to: '/companies', superAdmin: true, icon: <ApartmentOutlinedIcon /> },
        { label: t('Roles'), to: '/roles', superAdmin: true, icon: <AccountTreeOutlinedIcon /> },
        { label: t('Employees'), to: '/employees', permission: 'employee:show', icon: <GroupsOutlinedIcon /> },
        { label: t('Rates'), to: '/parking-rates', permission: 'rate:show', icon: <PaymentsOutlinedIcon /> },
      ],
    },
    {
      key: 'insights', label: t('Insights'), icon: <AssessmentOutlinedIcon />, items: [
        { label: t('Reports'), to: '/reports', permission: 'report:show', icon: <AssessmentOutlinedIcon /> },
        { label: t('Audit logs'), to: '/audit-logs', permission: 'audit:show', icon: <HistoryOutlinedIcon /> },
      ],
    },
    {
      key: 'system', label: t('System'), icon: <SettingsBackupRestoreOutlinedIcon />, items: [
        { label: t('Software settings'), to: '/software-settings', superAdmin: true, icon: <SettingsOutlinedIcon /> },
        { label: t('Backup'), to: '/system-maintenance', superAdmin: true, icon: <SettingsBackupRestoreOutlinedIcon /> },
      ],
    },
  ], [t]);

  const canView = (item: TreeItem) => Boolean(user?.isSuperAdmin || (!item.superAdmin && (!item.permission || user?.permissions.includes(item.permission))));
  const visibleGroups = groups.map((group) => ({ ...group, items: group.items.filter(canView) })).filter((group) => group.items.length > 0);
  const navigation = <NavigationTree groups={visibleGroups} expanded={expanded} activePath={location.pathname} companyName={companyName} companyLogo={companyLogo} workspaceLabel={t('Parking workspace')} securityLabel={t('Secure parking operations')} onToggle={(key) => setExpanded((current) => ({ ...current, [key]: !current[key] }))} onNavigate={() => setMobileOpen(false)} />;

  return <Box minHeight="100vh" display="flex" alignItems="stretch" gap={{ md: 1.5 }} p={{ xs: 1, sm: 1.25, md: 1.5 }} bgcolor="background.default">
    {user && <Drawer variant="permanent" sx={{ display: { xs: 'none', md: 'block' }, width: drawerWidth, flexShrink: 0, '& .MuiDrawer-paper': { position: 'relative', width: drawerWidth, height: '100%', boxSizing: 'border-box', border: 0, borderRadius: 3, overflow: 'hidden', bgcolor: 'background.paper', boxShadow: 2 } }}>{navigation}</Drawer>}
    {user && <Drawer variant="temporary" open={mobileOpen} onClose={() => setMobileOpen(false)} ModalProps={{ keepMounted: true }} sx={{ display: { xs: 'block', md: 'none' }, '& .MuiDrawer-paper': { width: drawerWidth } }}>{navigation}</Drawer>}
    <Box flexGrow={1} minWidth={0} display="flex" flexDirection="column">
      <AppBar position="sticky" elevation={0} sx={(theme) => ({ overflow: 'hidden', borderRadius: 3, background: `linear-gradient(115deg, ${theme.palette.primary.main}, ${theme.palette.primary.dark})`, borderBottom: `1px solid ${alpha(theme.palette.common.white, 0.14)}`, '&::after': { content: '""', position: 'absolute', zIndex: 0, width: 310, height: 310, right: -100, top: -190, borderRadius: '50%', bgcolor: alpha(theme.palette.secondary.main, 0.24) } })}>
        <Toolbar sx={{ position: 'relative', zIndex: 1, minHeight: { xs: 64, md: 72 } }}>
          <Stack direction="row" alignItems="center" spacing={1.25} minWidth={0} flexGrow={1}>
            {user && <IconButton color="inherit" onClick={() => setMobileOpen(true)} sx={{ display: { md: 'none' } }} aria-label={t('Menu')}><MenuIcon /></IconButton>}
            <Avatar variant="rounded" src={companyLogo ?? undefined} sx={(theme) => ({ width: 38, height: 38, bgcolor: alpha(theme.palette.common.white, 0.16), color: 'common.white', border: `1px solid ${alpha(theme.palette.common.white, 0.25)}` })}>{companyName.slice(0, 1)}</Avatar>
            <Typography variant="h6" component="span" fontWeight={900} noWrap>{companyName}</Typography>
          </Stack>
          {user && <Tooltip title={`${userName} · ${userRole}`}><Stack direction="row" spacing={1} alignItems="center" sx={(theme) => ({ mr: { xs: 0.5, md: 1.25 }, px: 1, py: 0.5, minWidth: 0, borderRadius: 2.5, display: { xs: 'none', lg: 'flex' }, bgcolor: alpha(theme.palette.common.white, 0.12), border: `1px solid ${alpha(theme.palette.common.white, 0.13)}` })}><Badge overlap="circular" variant="dot" color="secondary" anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}><Avatar src={user.photoUrl ?? undefined} sx={(theme) => ({ width: 34, height: 34, border: `2px solid ${alpha(theme.palette.secondary.light, 0.9)}` })}>{userName.slice(0, 1)}</Avatar></Badge><Box minWidth={0}><Typography variant="body2" fontWeight={800} noWrap maxWidth={175}>{userName}</Typography><Typography variant="caption" sx={{ display: 'block', lineHeight: 1.1, opacity: 0.76, textTransform: 'capitalize' }} noWrap>{userRole}</Typography></Box></Stack></Tooltip>}
          <Box sx={(theme) => ({ mr: 0.5, px: 0.75, height: 38, display: 'flex', alignItems: 'center', borderRadius: 2, bgcolor: alpha(theme.palette.common.white, 0.1), border: `1px solid ${alpha(theme.palette.common.white, 0.13)}` })}><TranslateOutlinedIcon fontSize="small" sx={{ mr: 0.25, opacity: 0.9 }} /><Select value={language} onChange={(event) => setLanguage(event.target.value as 'en' | 'hi' | 'ta')} variant="standard" sx={{ color: 'inherit', '& .MuiSvgIcon-root': { color: 'inherit' }, '&::before, &::after': { borderBottom: 0 }, minWidth: 47, fontWeight: 800 }} inputProps={{ 'aria-label': t('Language') }}><MenuItem value="en">EN</MenuItem><MenuItem value="hi">हिं</MenuItem><MenuItem value="ta">த</MenuItem></Select></Box>
          <Tooltip title={mode === 'dark' ? t('Light theme') : t('Dark theme')}><IconButton color="inherit" onClick={toggleMode} sx={(theme) => ({ mr: 0.5, bgcolor: alpha(theme.palette.common.white, 0.1), '&:hover': { bgcolor: alpha(theme.palette.common.white, 0.2) } })}>{mode === 'dark' ? <LightModeIcon /> : <DarkModeIcon />}</IconButton></Tooltip>
          {user && <Tooltip title={t('Sign out')}><IconButton onClick={signOut} sx={(theme) => ({ color: theme.palette.secondary.contrastText, bgcolor: theme.palette.secondary.main, boxShadow: `0 4px 12px ${alpha(theme.palette.secondary.dark, 0.32)}`, '&:hover': { bgcolor: theme.palette.secondary.dark } })}><LogoutIcon /></IconButton></Tooltip>}
        </Toolbar>
      </AppBar>
      <Container component="main" maxWidth="xl" sx={{ flexGrow: 1, width: '100%', px: { xs: 0.5, sm: 1.25, md: 2 }, py: { xs: 2, md: 3 } }}><Outlet /></Container>
    </Box>
  </Box>;
}

function NavigationTree({ groups, expanded, activePath, companyName, companyLogo, workspaceLabel, securityLabel, onToggle, onNavigate }: { groups: TreeGroup[]; expanded: Record<string, boolean>; activePath: string; companyName: string; companyLogo?: string | null; workspaceLabel: string; securityLabel: string; onToggle: (key: string) => void; onNavigate: () => void }) {
  return <Box display="flex" flexDirection="column" height="100%">
    <Box px={2.25} py={2.5} sx={(theme) => ({ background: `linear-gradient(145deg, ${alpha(theme.palette.primary.main, theme.palette.mode === 'dark' ? 0.3 : 0.1)}, transparent)` })}><Stack direction="row" alignItems="center" spacing={1.25}><Avatar variant="rounded" src={companyLogo ?? undefined} sx={{ width: 40, height: 40, bgcolor: 'primary.main', fontWeight: 800 }}>{companyName.slice(0, 1)}</Avatar><Box minWidth={0}><Typography variant="caption" color="text.secondary">{workspaceLabel}</Typography><Typography fontWeight={900} lineHeight={1.2} noWrap>{companyName}</Typography></Box></Stack></Box>
    <Divider />
    <List component="nav" sx={{ px: 1.25, py: 1.5, flexGrow: 1, overflowY: 'auto' }}>{groups.map((group) => <Box key={group.key} mb={1.25}>
      <ListItemButton onClick={() => onToggle(group.key)} aria-expanded={expanded[group.key]} sx={(theme) => ({ borderRadius: 2.5, px: 1.25, py: 0.85, color: 'text.secondary', bgcolor: alpha(theme.palette.primary.main, theme.palette.mode === 'dark' ? 0.18 : 0.06), border: `1px solid ${alpha(theme.palette.primary.main, theme.palette.mode === 'dark' ? 0.24 : 0.1)}`, '& .MuiListItemIcon-root': { color: 'secondary.main' }, '&:hover': { bgcolor: alpha(theme.palette.secondary.main, theme.palette.mode === 'dark' ? 0.16 : 0.1) } })}><ListItemIcon sx={{ minWidth: 36 }}>{group.icon}</ListItemIcon><ListItemText primary={group.label} primaryTypographyProps={{ fontWeight: 900, variant: 'caption', sx: { letterSpacing: 0.65, textTransform: 'uppercase' } }} />{expanded[group.key] ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}</ListItemButton>
      <Collapse in={expanded[group.key]} timeout="auto" unmountOnExit><Box sx={(theme) => ({ ml: 2.9, mt: 0.75, pl: 0.75, borderLeft: `2px solid ${alpha(theme.palette.primary.main, theme.palette.mode === 'dark' ? 0.3 : 0.17)}` })}><List disablePadding>{group.items.map((item) => {
        const selected = activePath === item.to || (item.to !== '/app' && activePath.startsWith(`${item.to}/`));
        return <ListItemButton key={item.to} component={Link} to={item.to} selected={selected} onClick={onNavigate} sx={(theme) => ({ position: 'relative', borderRadius: 2, mb: 0.35, pl: 1.25, minHeight: 44, color: selected ? 'primary.main' : 'text.primary', '&::before': { content: '""', position: 'absolute', left: -6, width: 8, height: 8, borderRadius: '50%', bgcolor: selected ? 'primary.main' : alpha(theme.palette.text.secondary, 0.4), transition: 'all 160ms ease' }, '& .MuiListItemIcon-root': { color: selected ? 'primary.main' : 'text.secondary' }, '&:hover': { bgcolor: alpha(theme.palette.secondary.main, theme.palette.mode === 'dark' ? 0.18 : 0.1), '&::before': { bgcolor: 'secondary.main', transform: 'scale(1.25)' } }, '&.Mui-selected': { bgcolor: alpha(theme.palette.primary.main, theme.palette.mode === 'dark' ? 0.28 : 0.12), boxShadow: `inset 3px 0 ${theme.palette.primary.main}` }, '&.Mui-selected:hover': { bgcolor: alpha(theme.palette.primary.main, theme.palette.mode === 'dark' ? 0.34 : 0.16) } })}><ListItemIcon sx={{ minWidth: 36 }}>{item.icon}</ListItemIcon><ListItemText primary={item.label} primaryTypographyProps={{ fontWeight: selected ? 800 : 600, variant: 'body2' }} /></ListItemButton>;
      })}</List></Box></Collapse>
    </Box>)}</List>
    <Box px={2.25} py={1.75}><Divider sx={{ mb: 1.5 }} /><Typography variant="caption" color="text.secondary">{securityLabel}</Typography></Box>
  </Box>;
}
