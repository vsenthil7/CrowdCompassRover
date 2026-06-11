import { useCallback, useEffect, useState } from "react";
import * as api from "../lib/api";
import type { VenueAvailability } from "../lib/types";

/** Fetches availability for a set of venue ids and exposes a lookup map.
 *
 * Used by the results list to overlay live open/crowd status onto search hits. Failures are
 * swallowed per-venue (availability is supplementary — a failed lookup must never blank a
 * result), and an optional `at` time lets the UI ask "will it be open at kickoff?".
 */
export function useAvailability(venueIds: string[], at?: string) {
  const [map, setMap] = useState<Record<string, VenueAvailability>>({});
  const [loading, setLoading] = useState(false);

  const key = venueIds.join(",");

  const load = useCallback(async () => {
    if (venueIds.length === 0) {
      setMap({});
      return;
    }
    setLoading(true);
    const results = await Promise.all(
      venueIds.map(async (id) => {
        try {
          return await api.availability(id, at);
        } catch {
          return null;
        }
      }),
    );
    const next: Record<string, VenueAvailability> = {};
    for (const r of results) {
      if (r) next[r.venue_id] = r;
    }
    setMap(next);
    setLoading(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, at]);

  useEffect(() => {
    void load();
  }, [load]);

  return { availability: map, loading, reload: load };
}
