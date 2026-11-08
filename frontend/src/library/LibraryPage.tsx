import { useSearchParams, Link } from "react-router";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { fetchApi } from "../api";
import { ApiError } from "../api";

const VALID_TYPES = ["", "movie", "series"];
const VALID_STATUSES = ["", "requested", "approved", "searching", "downloading", "importing", "available"];

interface TitleItem {
  id: number;
  type: string;
  tmdb_id: number | null;
  tvdb_id: number | null;
  imdb_id: string | null;
  name: string;
  year?: number | null;
  overview: string | null;
  poster_path: string | null;
  status: string;
  monitored: boolean;
  tags: string[];
  added_at: string;
}

interface TitlesResponse {
  items: TitleItem[];
  total: number;
  page: number;
  page_size: number;
}

function parsePage(raw: string | null): number {
  if (!raw) return 1;
  const n = Number(raw);
  return Number.isInteger(n) && n >= 1 ? n : 1;
}

export default function LibraryPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  const rawType = searchParams.get("type");
  const rawStatus = searchParams.get("status");
  const rawQ = searchParams.get("q");
  const rawPage = searchParams.get("page");

  const type = VALID_TYPES.includes(rawType ?? "") ? (rawType ?? "") : "";
  const status = VALID_STATUSES.includes(rawStatus ?? "") ? (rawStatus ?? "") : "";
  const q = rawQ ?? "";
  const page = parsePage(rawPage);

  const query = useQuery<TitlesResponse>({
    queryKey: ["titles", { type, status, q, page }],
    queryFn: async () => {
      const qs = new URLSearchParams();
      qs.set("page", String(page));
      if (type) qs.set("type", type);
      if (status) qs.set("status", status);
      if (q) qs.set("q", q);
      return fetchApi("/api/v1/titles?" + qs.toString()) as Promise<TitlesResponse>;
    },
    placeholderData: keepPreviousData,
  });

  function updateParam(key: string, value: string | null) {
    const next = new URLSearchParams(searchParams);
    if (value) {
      next.set(key, value);
    } else {
      next.delete(key);
    }
    next.delete("page");
    setSearchParams(next);
  }

  function handleTypeChange(e: React.ChangeEvent<HTMLSelectElement>) {
    updateParam("type", e.target.value || null);
  }

  function handleStatusChange(e: React.ChangeEvent<HTMLSelectElement>) {
    updateParam("status", e.target.value || null);
  }

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    const form = e.currentTarget;
    const input = form.querySelector<HTMLInputElement>('input[name="q"]');
    updateParam("q", input?.value?.trim() ?? null);
  }

  function handlePageChange(delta: number) {
    const next = new URLSearchParams(searchParams);
    next.set("page", String(page + delta));
    setSearchParams(next);
  }

  const totalPages = Math.max(1, Math.ceil((query.data?.total ?? 0) / (query.data?.page_size ?? 50)));

  return (
    <div>
      <h2 className="text-xl font-semibold">Library</h2>
      <div className="flex flex-wrap gap-2 mt-4 items-end">
        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium">Type</span>
          <select
            name="type"
            value={type}
            onChange={handleTypeChange}
            className="px-3 py-2 rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
          >
            <option value="">All types</option>
            <option value="movie">Movies</option>
            <option value="series">Series</option>
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium">Status</span>
          <select
            name="status"
            value={status}
            onChange={handleStatusChange}
            className="px-3 py-2 rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
          >
            <option value="">All statuses</option>
            <option value="requested">Requested</option>
            <option value="approved">Approved</option>
            <option value="searching">Searching</option>
            <option value="downloading">Downloading</option>
            <option value="importing">Importing</option>
            <option value="available">Available</option>
          </select>
        </label>
        <form onSubmit={handleSearchSubmit} className="flex flex-col gap-1">
          <label htmlFor="search" className="text-sm font-medium">Search</label>
          <input
            id="search"
            name="q"
            type="text"
            defaultValue={q}
            key={q}
            placeholder="Search titles..."
            className="px-3 py-2 rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
          />
        </form>
      </div>
      {query.isPending ? (
        <div className="mt-4">Loading...</div>
      ) : query.isError ? (
        <div role="alert">Couldn't load the library.</div>
      ) : (
        <div className="mt-4">
          <p className="text-sm">
            {query.data?.total === 1 ? "1 title" : `${query.data?.total ?? 0} titles`}
          </p>
          {((query.data?.items?.length ?? 0) === 0) ? (
            <p className="mt-2">
              {type || status || q ? "No titles match these filters." : "No titles yet."}
            </p>
          ) : (
            <ul className="mt-2 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {query.data?.items.map((item) => (
                <li key={item.id}>
                    <Link
                      to={`/titles/${item.id}`}
                      className="block p-3 rounded border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                  >
                    <div className="font-medium">
                      <span>{item.name}</span>{" "}
                      {item.year ? <> (<span>{item.year}</span>)</> : null}
                    </div>
                    <div className="text-xs mt-1 text-gray-500 dark:text-gray-400 capitalize">
                      {item.type} &middot; {item.status}
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <p className="text-sm">
            Page {page} of {totalPages}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => handlePageChange(-1)}
              disabled={page <= 1}
              className="px-3 py-1 rounded border border-gray-300 dark:border-gray-600 disabled:opacity-50"
            >
              Previous page
            </button>
            <button
              onClick={() => handlePageChange(1)}
              disabled={page >= totalPages}
              className="px-3 py-1 rounded border border-gray-300 dark:border-gray-600 disabled:opacity-50"
            >
              Next page
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
