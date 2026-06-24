import { X } from "lucide-react";
import { Button } from "./ui/Button";

export default function Modal({ open, title, description, children, onClose, footer }) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[80] grid place-items-center bg-gray-950/45 p-4 backdrop-blur-sm">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-hidden rounded-3xl bg-white shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-gray-200 p-6">
          <div>
            <h2 className="text-xl font-semibold text-gray-950">{title}</h2>
            {description ? <p className="mt-1 text-sm text-gray-500">{description}</p> : null}
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-5 w-5" />
          </Button>
        </div>
        <div className="max-h-[62vh] overflow-y-auto p-6">{children}</div>
        {footer ? <div className="border-t border-gray-200 bg-gray-50 p-4">{footer}</div> : null}
      </div>
    </div>
  );
}
