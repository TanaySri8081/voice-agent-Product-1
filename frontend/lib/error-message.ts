export function getErrorMessage(error: unknown, fallback = "Internal Server Error") {
  return error instanceof Error ? error.message : fallback;
}
