"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { addToShortlist, listShortlists } from "@/lib/api";
import type { ShortlistSummary } from "@/types";

interface AddToShortlistButtonProps {
	personId: string;
}

export function AddToShortlistButton({ personId }: AddToShortlistButtonProps) {
	const [shortlists, setShortlists] = useState<ShortlistSummary[] | null>(null);
	const [showDropdown, setShowDropdown] = useState(false);
	const [adding, setAdding] = useState<string | null>(null);
	const [added, setAdded] = useState<string | null>(null);
	const [addError, setAddError] = useState<string | null>(null);
	const dropdownRef = useRef<HTMLDivElement>(null);

	useEffect(() => {
		if (!showDropdown) return;
		function handleClickOutside(e: MouseEvent) {
			if (
				dropdownRef.current &&
				!dropdownRef.current.contains(e.target as Node)
			) {
				setShowDropdown(false);
			}
		}
		function handleEscape(e: KeyboardEvent) {
			if (e.key === "Escape") setShowDropdown(false);
		}
		document.addEventListener("mousedown", handleClickOutside);
		document.addEventListener("keydown", handleEscape);
		return () => {
			document.removeEventListener("mousedown", handleClickOutside);
			document.removeEventListener("keydown", handleEscape);
		};
	}, [showDropdown]);

	async function handleOpenDropdown() {
		if (!shortlists) {
			try {
				const data = await listShortlists();
				setShortlists(data);
			} catch (e) {
				setAddError(
					e instanceof Error ? e.message : "Failed to load shortlists",
				);
			}
		}
		setShowDropdown((v) => !v);
	}

	async function handleAdd(shortlistId: string) {
		setAdding(shortlistId);
		setAddError(null);
		try {
			await addToShortlist(shortlistId, personId);
			setAdded(shortlistId);
		} catch (e: unknown) {
			setAddError(e instanceof Error ? e.message : "Failed");
		} finally {
			setAdding(null);
			setShowDropdown(false);
		}
	}

	return (
		<div className="relative" ref={dropdownRef}>
			<button
				type="button"
				onClick={handleOpenDropdown}
				aria-haspopup="menu"
				aria-expanded={showDropdown}
				className="text-xs px-2 py-1 border border-gray-200 rounded hover:bg-gray-50 text-gray-600"
				title="Add to shortlist"
			>
				{added ? "✓" : "+ List"}
			</button>
			{showDropdown && (
				<div className="absolute right-0 top-7 z-10 bg-white border border-gray-200 rounded shadow-md min-w-40">
					{shortlists === null ? (
						<p className="text-xs text-gray-400 p-2">Loading…</p>
					) : shortlists.length === 0 ? (
						<p className="text-xs text-gray-400 p-2">
							No shortlists.{" "}
							<Link href="/shortlists" className="text-blue-500 underline">
								Create one
							</Link>
						</p>
					) : (
						shortlists.map((sl) => (
							<button
								key={sl.id}
								type="button"
								disabled={adding === sl.id}
								onClick={() => handleAdd(sl.id)}
								className="w-full text-left text-xs px-3 py-2 hover:bg-gray-50 text-gray-700 truncate"
							>
								{adding === sl.id ? "Adding…" : sl.name}
							</button>
						))
					)}
				</div>
			)}
			{addError && <p className="text-xs text-red-400 mt-1">{addError}</p>}
		</div>
	);
}
