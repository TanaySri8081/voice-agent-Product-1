export default function LoadingState() {
  return (
    <div className="space-y-3 rounded-3xl border border-gray-200 bg-white p-5">
      {[0, 1, 2, 3].map((item) => (
        <div key={item} className="flex animate-pulse items-center gap-4">
          <div className="h-10 w-10 rounded-2xl bg-gray-100" />
          <div className="flex-1 space-y-2">
            <div className="h-3 w-1/3 rounded bg-gray-100" />
            <div className="h-3 w-2/3 rounded bg-gray-100" />
          </div>
          <div className="h-8 w-20 rounded-full bg-gray-100" />
        </div>
      ))}
    </div>
  );
}
