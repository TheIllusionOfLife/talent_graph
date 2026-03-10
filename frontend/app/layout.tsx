import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
	variable: "--font-geist-sans",
	subsets: ["latin"],
});

const geistMono = Geist_Mono({
	variable: "--font-geist-mono",
	subsets: ["latin"],
});

export const metadata: Metadata = {
	title: "Talent Graph",
	description: "Discover hidden experts using knowledge graphs",
};

export default function RootLayout({
	children,
}: Readonly<{
	children: React.ReactNode;
}>) {
	return (
		<html lang="en">
			<body
				className={`${geistSans.variable} ${geistMono.variable} antialiased`}
			>
				<nav className="border-b border-gray-200 bg-white px-4 py-3 flex items-center gap-6 text-sm">
					<Link
						href="/"
						className="font-semibold text-gray-900 hover:text-blue-700"
					>
						Talent Graph
					</Link>
					<Link
						href="/shortlists"
						className="text-gray-500 hover:text-gray-900"
					>
						Shortlists
					</Link>
					<Link href="/searches" className="text-gray-500 hover:text-gray-900">
						Saved Searches
					</Link>
				</nav>
				{children}
			</body>
		</html>
	);
}
