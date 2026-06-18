import { CreditCard, Download, Receipt, Sparkles } from "lucide-react";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import DataTable from "../components/DataTable";

export default function Billing() {
  const invoices = [
    { id: "INV-001", date: "Jun 01, 2026", amount: "$1,284.00", status: "Paid" },
    { id: "INV-002", date: "May 01, 2026", amount: "$985.50", status: "Paid" },
    { id: "INV-003", date: "Apr 01, 2026", amount: "$750.00", status: "Paid" },
  ];

  const columns = [
    { key: "id", header: "Invoice ID" },
    { key: "date", header: "Billing Date" },
    { key: "amount", header: "Amount" },
    {
      key: "status",
      header: "Status",
      render: (row) => <Badge tone="success">{row.status}</Badge>,
    },
    {
      key: "action",
      header: "Action",
      render: () => (
        <Button variant="secondary" size="sm">
          <Download className="h-3.5 w-3.5" /> Download
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-gray-950">Billing & Subscription</h1>
        <p className="mt-2 text-sm text-gray-500">Manage your subscription plans, credits, and invoices.</p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <article className="panel rounded-3xl p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">Current Plan</span>
              <Badge tone="dark">Premium Pro</Badge>
            </div>
            <p className="mt-4 text-3xl font-semibold text-gray-950">$49/month</p>
            <p className="mt-1 text-sm text-gray-500">Includes 5,000 AI minutes/month</p>
          </div>
          <div className="mt-6 flex gap-2">
            <Button className="w-full">Upgrade</Button>
            <Button variant="secondary" className="w-full">Manage Plan</Button>
          </div>
        </article>

        <article className="panel rounded-3xl p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">Credits Remaining</span>
              <Sparkles className="h-4 w-4 text-amber-500" />
            </div>
            <p className="mt-4 text-3xl font-semibold text-gray-950">14,280 mins</p>
            <p className="mt-1 text-sm text-gray-500">Expires on Jul 01, 2026</p>
          </div>
          <div className="mt-6">
            <Button variant="secondary" className="w-full">Buy Top-up Credits</Button>
          </div>
        </article>

        <article className="panel rounded-3xl p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">Payment Method</span>
              <CreditCard className="h-4 w-4 text-gray-500" />
            </div>
            <p className="mt-4 text-lg font-semibold text-gray-950">Visa ending in 4242</p>
            <p className="mt-1 text-sm text-gray-500">Next billing date: Jul 01, 2026</p>
          </div>
          <div className="mt-6">
            <Button variant="secondary" className="w-full">Update Payment Details</Button>
          </div>
        </article>
      </div>

      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <Receipt className="h-5 w-5 text-gray-500" />
          <h2 className="text-lg font-semibold text-gray-950">Invoice History</h2>
        </div>
        <DataTable columns={columns} rows={invoices} />
      </section>
    </div>
  );
}
