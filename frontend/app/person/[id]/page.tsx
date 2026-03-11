import Link from "next/link";
import { AddToShortlistButton } from "@/components/AddToShortlistButton";
import { PersonBrief } from "@/components/PersonBrief";
import { getPerson } from "@/lib/api";
import type { PersonDetail } from "@/types";

interface PersonPageProps {
	params: Promise<{ id: string }>;
	searchParams: Promise<{ q?: string }>;
}

export default async function PersonPage({
	params,
	searchParams,
}: PersonPageProps) {
	const { id } = await params;
	const { q: seedText } = await searchParams;

	let person: PersonDetail | undefined;
	let error: string | null = null;

	try {
		person = await getPerson(id);
	} catch (e) {
		error = e instanceof Error ? e.message : "Unknown error";
	}

	if (error) {
		return (
			<main className="min-h-screen bg-gray-50 px-4 py-10">
				<div className="max-w-3xl mx-auto">
					<Link href="/" className="text-blue-600 hover:underline text-sm">
						← Back
					</Link>
					<p className="text-red-500 mt-4">{error}</p>
				</div>
			</main>
		);
	}

	if (!person) return null;

	return (
		<main className="min-h-screen bg-gray-50 px-4 py-10">
			<div className="max-w-3xl mx-auto">
				<div className="flex items-center gap-2 mb-6">
					<Link href="/" className="text-blue-600 hover:underline text-sm">
						← Search
					</Link>
					<span className="text-gray-400">/</span>
					<span className="text-sm text-gray-600">{person.name}</span>
				</div>

				{/* Header */}
				<div className="bg-white border border-gray-200 rounded-lg p-6 mb-4">
					<div className="flex items-start justify-between">
						<div>
							<h1 className="text-2xl font-bold text-gray-900">
								{person.name}
							</h1>
							{person.org && (
								<p className="text-gray-500 text-sm mt-1">
									{person.org.name}
									{person.org.country_code && ` · ${person.org.country_code}`}
								</p>
							)}
						</div>
						<div className="flex items-center gap-2">
							<AddToShortlistButton personId={person.id} />
							<Link
								href={`/discovery/person/${person.id}`}
								className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700"
							>
								Discover similar
							</Link>
						</div>
					</div>

					<div className="flex flex-wrap gap-3 mt-4 text-sm text-gray-500">
						{person.github_login && (
							<a
								href={`https://github.com/${person.github_login}`}
								target="_blank"
								rel="noopener noreferrer"
								className="text-blue-500 hover:underline"
							>
								GitHub: @{person.github_login}
							</a>
						)}
						{person.openalex_author_id && (
							<a
								href={`https://openalex.org/authors/${person.openalex_author_id}`}
								target="_blank"
								rel="noopener noreferrer"
								className="text-blue-500 hover:underline"
							>
								OpenAlex: {person.openalex_author_id}
							</a>
						)}
						{person.orcid && (
							<a
								href={`https://orcid.org/${person.orcid}`}
								target="_blank"
								rel="noopener noreferrer"
								className="text-blue-500 hover:underline"
							>
								ORCID: {person.orcid}
							</a>
						)}
						{person.homepage && (
							<a
								href={person.homepage}
								target="_blank"
								rel="noopener noreferrer"
								className="text-blue-500 hover:underline"
							>
								Homepage
							</a>
						)}
						{person.email && <span>{person.email}</span>}
						{person.hidden_expert_score !== null && (
							<span className="text-purple-600 font-medium">
								Hidden Expert Score: {person.hidden_expert_score.toFixed(3)}
							</span>
						)}
					</div>
				</div>

				{/* AI Brief */}
				{seedText && <PersonBrief personId={person.id} seedText={seedText} />}

				{/* Papers */}
				{person.papers.length > 0 && (
					<section className="mb-4">
						<h2 className="text-lg font-semibold text-gray-800 mb-2">
							Papers ({person.papers.length})
						</h2>
						<div className="space-y-2">
							{person.papers
								.sort(
									(a, b) =>
										(b.publication_year ?? 0) - (a.publication_year ?? 0),
								)
								.map((p) => (
									<div
										key={p.id}
										className="bg-white border border-gray-200 rounded p-3"
									>
										<p className="text-sm font-medium text-gray-800">
											{p.title}
										</p>
										<div className="flex gap-3 mt-1 text-xs text-gray-400">
											{p.publication_year && <span>{p.publication_year}</span>}
											<span>{p.citation_count} citations</span>
											{p.concepts.slice(0, 3).map((c) => (
												<span
													key={c}
													className="bg-gray-100 px-1.5 py-0.5 rounded"
												>
													{c}
												</span>
											))}
										</div>
									</div>
								))}
						</div>
					</section>
				)}

				{/* Repos */}
				{person.repos.length > 0 && (
					<section>
						<h2 className="text-lg font-semibold text-gray-800 mb-2">
							Repositories ({person.repos.length})
						</h2>
						<div className="space-y-2">
							{person.repos.map((r) => (
								<div
									key={r.id}
									className="bg-white border border-gray-200 rounded p-3"
								>
									<p className="text-sm font-medium text-gray-800">
										{r.full_name}
									</p>
									{r.description && (
										<p className="text-xs text-gray-500 mt-0.5">
											{r.description}
										</p>
									)}
									<div className="flex gap-3 mt-1 text-xs text-gray-400">
										{r.language && <span>{r.language}</span>}
										<span>★ {r.stars}</span>
										{r.topics.slice(0, 3).map((t) => (
											<span
												key={t}
												className="bg-gray-100 px-1.5 py-0.5 rounded"
											>
												{t}
											</span>
										))}
									</div>
								</div>
							))}
						</div>
					</section>
				)}
			</div>
		</main>
	);
}
