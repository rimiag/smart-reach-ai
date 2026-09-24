'use client';

import { Suspense } from 'react';
import AppShell from '@/components/AppShell';
import Skeleton from '@/components/Skeleton';
import DashboardLeads from '@/components/DashboardLeads';

/**
 * The main Leads page (sidebar "Leads"): every lead across campaigns with
 * manual create, campaign re-assignment and one-off manual emailing.
 * ?campaign_id=N (links from campaign pages) preselects the campaign filter.
 */
function LeadsContent() {
  return (
    <AppShell title="Leads" description="All your leads across campaigns">
      <DashboardLeads />
    </AppShell>
  );
}

export default function LeadsPage() {
  return (
    <Suspense fallback={<AppShell title="Leads"><Skeleton rows={5} /></AppShell>}>
      <LeadsContent />
    </Suspense>
  );
}
