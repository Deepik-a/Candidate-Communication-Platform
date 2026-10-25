import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import ThemeRegistry from '@/components/ThemeRegistry';
import { ToastProvider } from '@/context/ToastContext';
import './globals.css';

const inter = Inter({ subsets: ['latin'], display: 'swap' });

export const metadata: Metadata = {
  title: 'Candidate Communication Platform',
  description: 'Recruiter platform to communicate with candidates and track communication journeys.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <ThemeRegistry>
          <ToastProvider>
            {children}
          </ToastProvider>
        </ThemeRegistry>
      </body>
    </html>
  );
}
