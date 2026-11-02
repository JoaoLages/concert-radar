# concert-radar

Find upcoming concerts in Portugal and Spain for **every artist in your Spotify playlists**, not just the ones you follow or play most.

Once a day, a GitHub Actions job reads your playlists, collects upcoming concerts from Portuguese and Spanish ticketing and listings sites, matches them against your artists, and publishes the result as a web page on GitHub Pages. Shows that appeared in the last week are marked **NEW**.

Log in with Spotify on the page to see only the artists you **follow on Spotify**. The page lists your playlist artists so you can follow the ones you care about (those with upcoming shows first), and unfollow them again. Follows are real Spotify follows, so they're the same on every device. Without logging in, the page shows every match from your playlists.

## Sources

| Country | Site | How artists are matched |
|---|---|---|
| Portugal | [BOL](https://www.bol.pt) | Artist name in the event title |
| Portugal | [Ticketline](https://www.ticketline.pt) | Artist name in the event title |
| Spain | [La Ganzúa](https://www.laganzua.net) | Performer name |

Portuguese ticketing is split by venue and each site holds its own shows, so no single site covers everything. Not covered: Blueticket (which sells many MEO Arena shows), See Tickets, Bandsintown, DICE and Shotgun, which block automated access.

Matching by title is a heuristic. It skips tribute shows, and a short name like "Miguel" only matches when it stands alone in its part of the title, so it won't match "Miguel Araújo". Expect the odd false match, especially when two acts share a name.

**Terms of use:** this tool reads public listing pages. Some of these sites' terms restrict automated access or reuse of their content. Check them and decide for yourself before running it.

## Set up your own

You need a Spotify account with **Premium**: Spotify only lets Premium accounts own developer apps.

1. **Fork this repo.**
2. **Create a Spotify app** in the [developer dashboard](https://developer.spotify.com/dashboard):
   - Redirect URIs: `http://127.0.0.1:8888/callback` (for the one-time login below; Spotify rejects `localhost`) and your page's address, `https://<your-user>.github.io/concert-radar/` (for logging in on the page)
   - API: Web API
   - Copy the Client ID and Client secret from the app's settings.
3. **Get a refresh token** by logging in once, locally. Install [uv](https://docs.astral.sh/uv/), then:
   ```sh
   export SPOTIFY_CLIENT_ID=... SPOTIFY_CLIENT_SECRET=...
   uv run concert-radar login
   ```
   A browser tab asks you to allow read access to your playlists; the token is printed when you accept.
4. **Add three repository secrets** (Settings → Secrets and variables → Actions): `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REFRESH_TOKEN`.
5. **Turn on GitHub Pages** (Settings → Pages → Source: GitHub Actions).
6. **Run the workflow** once from the Actions tab ("Build concerts page" → Run workflow). After that it runs every day.

Your page lives at `https://<your-user>.github.io/concert-radar/`. On a public repo, the page is public too. Only you can log in on it: Spotify limits developer apps to the account that owns them plus up to five users added under User Management in the dashboard.

Only playlists you own or collaborate on are read: Spotify doesn't give developer apps the tracks of playlists you merely follow.

## Run locally

```sh
export SPOTIFY_CLIENT_ID=... SPOTIFY_CLIENT_SECRET=... SPOTIFY_REFRESH_TOKEN=...
uv run concert-radar build --out site --page-url http://127.0.0.1:8888/callback
open site/index.html
```

A full run makes a few hundred requests with a pause between each, so it takes several minutes.
