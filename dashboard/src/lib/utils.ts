import type { ServerStatus } from "@/types";
import { type ClassValue, clsx } from "clsx";
import { toast } from "sonner";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const fetcherSWR = async (
  url: string,
  method?: string,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  body?: any | null,
) => {
  const response = await fetch(url, {
    method: method || "GET",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : null,
  });

  if (response.ok) return await response.json();

  console.error("Error fetching data:", response);

  let errorMessage = response.statusText;
  try {
    const errorData = await response.json();
    if (errorData.detail) errorMessage = errorData.detail;
    if (typeof errorMessage === "object") {
      errorMessage = JSON.stringify(errorMessage);
    }
  } catch {
    // Use default statusText if JSON parsing fails
    errorMessage = response.statusText;
  }

  toast.error(`Error: ${errorMessage}`);
  return undefined;
};

const fetchWithBaseUrl = async (
  endpoint: string,
  method?: string,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  body?: any | null,
) => {
  const BASE_URL = `http://${window.location.hostname}:${window.location.port}`;
  const url = `${BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    method: method || "GET",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : null,
  });

  if (response.ok) return await response.json();

  console.error("Error fetching data:", response);

  let errorMessage = response.statusText;
  try {
    const errorData = await response.json();
    if (errorData.detail) errorMessage = errorData.detail;
    if (typeof errorMessage === "object") {
      errorMessage = JSON.stringify(errorMessage);
    }
  } catch {
    // Fallback to statusText if JSON parsing fails
    errorMessage = response.statusText;
  }

  toast.error(`Error: ${errorMessage}`);
  return undefined;
};

// The robot that a control without a robot picker acts on: the only connected
// robot whose serial is not in `ignoredSerials`. null when there is none or more
// than one: the caller then sends nothing. There is no default robot.
const onlyRobotId = (
  serverStatus?: ServerStatus | null,
  ignoredSerials?: string[] | null,
): number | null => {
  const candidates = (serverStatus?.robot_status ?? [])
    .map((robot, index) => ({ robot, id: robot.robot_id ?? index }))
    .filter(
      ({ robot }) =>
        !(robot.device_name && ignoredSerials?.includes(robot.device_name)),
    );
  return candidates.length === 1 ? candidates[0].id : null;
};

export { cn, fetcherSWR as fetcher, fetchWithBaseUrl, onlyRobotId };
