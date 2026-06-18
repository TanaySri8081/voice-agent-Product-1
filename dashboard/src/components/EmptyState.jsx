import { Inbox } from "lucide-react";

export default function EmptyState({ title = "Nothing here yet", description = "New records will appear here automatically." }) {
  return (
    <div className="grid min-h-52 place-items-center rounded-3xl border border-dashed border-gray-300 bg-white p-8 text-center">
      <div>
        <div className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-gray-100 text-gray-500">
          <Inbox className="h-5 w-5" />
        </div>
        <p className="mt-4 text-sm font-semibold text-gray-950">{title}</p>
        <p className="mt-1 text-sm text-gray-500">{description}</p>
      </div>
    </div>
  );
}
