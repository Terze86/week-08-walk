export default function ErrorText({ error }: { error: Error | null | undefined }) {
  return error ? <p className="error">{error.message}</p> : null;
}
