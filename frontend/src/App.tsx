import React, { useState } from "react";
import type { UseMutationResult } from "@tanstack/react-query";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BrowserRouter } from "react-router";
import { useHealth } from "./health";
import { useTheme } from "./theme";
import { fetchApi, ApiError } from "./api";
import LibraryPage from "./library/LibraryPage";

function extractMessage(err: unknown): string {
  if (err && typeof err === "object" && "message" in err) {
    return (err as { message: unknown }).message as string;
  }
  return "An error occurred";
}

export default function App() {
  const { theme, toggleTheme } = useTheme();
  const { data, isLoading, error: healthError } = useHealth();

  const setupQuery = useQuery({
    queryKey: ["auth-setup"],
    queryFn: async () => fetchApi("/api/v1/auth/setup"),
  });

  const meQuery = useQuery({
    queryKey: ["auth-me"],
    queryFn: async () => {
      try {
        return await fetchApi("/api/v1/auth/me");
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          return null;
        }
        throw err;
      }
    },
    enabled: (setupQuery.data as { required?: boolean } | undefined)?.required === false,
  });

  const queryClient = useQueryClient();

  const setupMutation = useMutation({
    mutationFn: async (data: { name: string; password: string }) =>
      fetchApi("/api/v1/auth/setup", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: (data) => {
      if (data && typeof data === "object" && "name" in data) {
        queryClient.setQueryData(["auth-me"], data);
      }
    },
    onSettled: () => {
      queryClient.setQueryData(["auth-setup"], undefined);
      queryClient.invalidateQueries({ queryKey: ["auth-setup"] });
    },
  });

  const loginMutation = useMutation({
    mutationFn: async (data: { name: string; password: string }) =>
      fetchApi("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: (data) => {
      if (data && typeof data === "object" && "name" in data) {
        queryClient.setQueryData(["auth-me"], data);
      }
    },
  });

  const logoutMutation = useMutation({
    mutationFn: async () => fetchApi("/api/v1/auth/logout", { method: "POST" }),
    onSuccess: () => {
      queryClient.setQueryData(["auth-me"], null);
    },
  });

  let apiStatus: React.ReactNode;
  if (isLoading) {
    apiStatus = null;
  } else if (healthError || !data) {
    apiStatus = "API offline";
  } else {
    apiStatus = `API ${data.version}`;
  }

  const setupError = setupQuery.error as ApiError | null;
  const meError = meQuery.error as ApiError | null;

  const setupData = (setupQuery.data as { required?: boolean } | undefined);
  const setupRequired = setupData?.required === true;
  const user = meQuery.data as { name: string } | null | undefined;

  const btnLabel = theme === "light" ? "Switch to dark theme" : "Switch to light theme";

  return (
    <BrowserRouter>
      <div className="min-h-screen">
        <header className="p-4">
          <h1 className="text-2xl font-bold">All-Togetharr</h1>
          {apiStatus && <p className="text-sm mt-1">{apiStatus}</p>}
          {user && (
            <p className="text-sm mt-1">Signed in as {user.name}</p>
          )}
          <div className="flex items-center gap-2 mt-2">
            <button onClick={toggleTheme} className="px-3 py-1 rounded">
              {btnLabel}
            </button>
            {user && (
              <button
                onClick={() => logoutMutation.mutate()}
                className="px-3 py-1 rounded"
              >
                Sign out
              </button>
            )}
          </div>
        </header>
        <main className="p-4">
          {(setupQuery.isLoading || meQuery.isLoading) ? (
            <div>Loading...</div>
          ) : setupError || meError ? (
            <p role="alert">{setupError?.message ?? meError?.message}</p>
          ) : setupRequired ? (
            <SetupForm setupMutation={setupMutation} />
          ) : user ? (
            <LibraryPage />
          ) : (
            <LoginForm loginMutation={loginMutation} />
          )}
        </main>
      </div>
    </BrowserRouter>
  );
}

function SetupForm({ setupMutation }: { setupMutation: UseMutationResult<unknown, Error, { name: string; password: string }> }) {
  const [password, setPassword] = useState("");
  const [submitAttempt, setSubmitAttempt] = useState(false);

  return (
    <>
      <h2 className="text-xl font-semibold mt-4">Create the admin account</h2>
      <form
        className="mt-4 space-y-3 max-w-sm"
        onSubmit={(e) => {
          e.preventDefault();
          const form = e.currentTarget;
          const name = (form.elements.namedItem("name") as HTMLInputElement).value;
          if (password.length < 8) {
            setSubmitAttempt(true);
            return;
          }
          setSubmitAttempt(false);
          setupMutation.mutate({ name, password });
        }}
      >
        <div>
          <label htmlFor="name" className="block text-sm font-medium">
            Name
          </label>
          <input
            id="name"
            name="name"
            type="text"
            autoComplete="username"
            className="mt-1 block w-full rounded border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 px-3 py-2"
          />
        </div>
        <div>
          <label htmlFor="password" className="block text-sm font-medium">
            Password
          </label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 block w-full rounded border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 px-3 py-2"
          />
        </div>
        <button
          type="submit"
          disabled={setupMutation.isPending}
          className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
        >
          Create admin account
        </button>
        {setupMutation.isError && (
          <p role="alert" className="text-red-600 dark:text-red-400">
            {extractMessage(setupMutation.error)}
          </p>
        )}
        {submitAttempt && password.length < 8 && (
          <p role="alert" className="text-red-600 dark:text-red-400">
            Password must be at least 8 characters
          </p>
        )}
      </form>
    </>
  );
}

function LoginForm({ loginMutation }: { loginMutation: UseMutationResult<unknown, Error, { name: string; password: string }> }) {
  return (
    <>
      <h2 className="text-xl font-semibold mt-4">Sign in</h2>
      <form
        className="mt-4 space-y-3 max-w-sm"
        onSubmit={(e) => {
          e.preventDefault();
          const form = e.currentTarget;
          const name = (form.elements.namedItem("name") as HTMLInputElement).value;
          const password = (form.elements.namedItem("password") as HTMLInputElement).value;
          loginMutation.mutate({ name, password });
        }}
      >
        <div>
          <label htmlFor="name" className="block text-sm font-medium">
            Name
          </label>
          <input
            id="name"
            name="name"
            type="text"
            autoComplete="username"
            className="mt-1 block w-full rounded border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 px-3 py-2"
          />
        </div>
        <div>
          <label htmlFor="password" className="block text-sm font-medium">
            Password
          </label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            className="mt-1 block w-full rounded border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 px-3 py-2"
          />
        </div>
        <button
          type="submit"
          disabled={loginMutation.isPending}
          className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
        >
          Sign in
        </button>
        {loginMutation.isError && (
          <p role="alert" className="text-red-600 dark:text-red-400">
            {extractMessage(loginMutation.error)}
          </p>
        )}
      </form>
    </>
  );
}
