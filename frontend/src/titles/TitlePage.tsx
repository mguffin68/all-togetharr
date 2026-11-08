import { useParams, Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { fetchApi, ApiError } from "../api";

interface Episode {
  id: number;
  season_number: number;
  episode_number: number;
  name: string | null;
  absolute_no: number | null;
  air_date: string | null;
  monitored: boolean;
  file_id: number | null;
}

interface Season {
  id: number;
  season_number: number;
  monitored: boolean;
  episodes: Episode[];
}

export interface TitleDetail {
  id: number;
  type: "movie" | "series";
  tmdb_id: number;
  tvdb_id: number | null;
  imdb_id: string | null;
  name: string;
  year: number | null;
  overview: string | null;
  poster_path: string | null;
  status: string;
  monitored: boolean;
  tags: string[];
  added_at: string;
  seasons: Season[];
}

const VALID_ID = /^[1-9]\d*$/;

export default function TitlePage() {
  const { id } = useParams() as { id: string };
  const validId = VALID_ID.test(id);

  const { data, isPending, error } = useQuery({
    queryKey: ["title", id],
    queryFn: () => fetchApi(`/api/v1/titles/${id}`) as Promise<TitleDetail>,
    enabled: validId,
  });

  if (!validId) {
    return (
      <>
        <p>Title not found.</p>
        <Link to="/" className="text-sm underline">Back to library</Link>
      </>
    );
  }

  if (isPending) {
    return <p>Loading...</p>;
  }

  if (error) {
    const apiError = error as ApiError;
    if (apiError.status === 404) {
      return (
        <>
          <p>Title not found.</p>
          <Link to="/" className="text-sm underline">Back to library</Link>
        </>
      );
    }
    return (
      <>
        <p role="alert">Couldn't load this title.</p>
        <Link to="/" className="text-sm underline">Back to library</Link>
      </>
    );
  }

  const title = data!;

  const sortedSeasons = [...title.seasons].sort((a, b) => {
    if (a.season_number === 0 && b.season_number !== 0) return 1;
    if (a.season_number !== 0 && b.season_number === 0) return -1;
    return a.season_number - b.season_number;
  });

  return (
    <div>
      <Link to="/" className="text-sm underline">Back to library</Link>
      <div className="flex flex-col sm:flex-row gap-4 mt-4">
        {title.poster_path && (
          <img
            src={`https://image.tmdb.org/t/p/w342${title.poster_path}`}
            alt={`Poster for ${title.name}`}
            loading="lazy"
            className="w-full max-w-[200px] h-auto rounded self-start"
          />
        )}
        <div>
          <h2 className="text-xl font-semibold">{title.name}</h2>
          <div className="flex flex-wrap gap-2 text-sm text-gray-600 dark:text-gray-400 mt-2">
            {title.year != null && <span>{title.year}</span>}
            <span>{title.type === "movie" ? "Movie" : "Series"}</span>
            <span>{title.status.charAt(0).toUpperCase() + title.status.slice(1)}</span>
          </div>
          {title.overview && <p className="mt-2">{title.overview}</p>}
          {title.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {title.tags.map((tag) => (
                <span key={tag} className="px-2 py-0.5 rounded text-xs bg-gray-200 dark:bg-gray-700">{tag}</span>
              ))}
            </div>
          )}
        </div>
      </div>
      {sortedSeasons.length > 0 && (
        <div className="mt-6">
          {sortedSeasons.map((season) => (
            <section key={season.id} aria-labelledby={`season-${season.season_number}`} className="mt-6">
              <h3 id={`season-${season.season_number}`} className="text-lg font-semibold">
                {season.season_number === 0 ? "Specials" : `Season ${season.season_number}`}
              </h3>
              <ul className="mt-2 divide-y divide-gray-200 dark:divide-gray-700">
                {[...season.episodes]
                  .sort((a, b) => a.episode_number - b.episode_number)
                  .map((ep) => (
                    <li key={ep.id} className="flex flex-wrap items-baseline gap-x-3 py-2">
                      <span className="flex-1 min-w-0">{ep.episode_number}. {ep.name ?? `Episode ${ep.episode_number}`}</span>
                      {ep.air_date && <span className="text-sm text-gray-600 dark:text-gray-400">{ep.air_date}</span>}
                      <span className={`px-2 py-0.5 rounded text-xs ${ep.file_id != null ? "text-green-700 dark:text-green-400 bg-green-100 dark:bg-green-900" : "bg-gray-200 dark:bg-gray-700"}`}>
                        {ep.file_id != null ? "Downloaded" : "Missing"}
                      </span>
                    </li>
                  ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
