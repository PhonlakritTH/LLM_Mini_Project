import "./globals.css";
export const metadata = { title: "PC Spec Builder" };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="th"><body>{children}</body></html>;
}
