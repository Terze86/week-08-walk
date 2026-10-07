export default function Placeholder({ title }: { title: string }) {
  return (
    <section>
      <h2>{title}</h2>
      <p className="muted">CODIS requests arrive in a later phase.</p>
    </section>
  );
}
