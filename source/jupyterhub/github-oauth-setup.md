# How to Setup GitHub App for JupyterHub

This guide will walk you through the process of setting up a GitHub App for your JupyterHub deployment.

## Prerequisites

1. A GitHub account
2. Administrative access to your JupyterHub deployment
3. Your JupyterHub domain/URL

## Step 1: Create a New GitHub Organization

1. Go to [github.com](https://github.com) and click on `+` icon in the top right
2. Click **New Organization** from the dropdown menu

   ![New Organization Option](../_static/images/github-1.png)

3. Fill in the organization details:
   - Enter your **Organization name** (e.g., "AUP-INT-TEST")
   - Provide a **Contact email**
   - Select whether this organization belongs to "My personal account" or "A business or institution"
   - Complete the verification puzzle
   - Accept the Terms of Service
   - Click **Next** to create the organization

   ![Organization Setup Form](../_static/images/github-2.png)

## Step 2: Create Teams to Assign Different Permissions

Teams allow you to organize members and control access to different resources in your JupyterHub deployment.

1. Navigate to your organization's **Teams** page
2. Click the **New team** button in the top right

   ![Teams Page](../_static/images/github-3.png)

3. Fill in the team creation form:
   - **Team name**: Use the same name as the key in your `values.yaml` `custom.teams.mapping` (e.g., "cpu", "gpu", "npu", "official")
   - **Description**: Add a description of what this team is for
   - **Team visibility**: Select **Visible** (recommended) - this allows all organization members to see the team
   - **Team notifications**: Choose whether to enable notifications
   - Click **Create team**

   ![Create Team Form](../_static/images/github-4.png)

4. Repeat this process to create all the teams you need for your resource mapping (e.g., cpu, gpu, npu, official, public, test)

## Step 3: Add Members to the Organization

1. Go to the **People** tab in your organization
2. Click the **Invite member** button in the top right

   ![People Page](../_static/images/github-5.png)

3. In the invitation dialog:
   - Enter the member's **email address or GitHub username**
   - Click **Invite**

   ![Invite Member Dialog](../_static/images/github-6.png)

4. Assign the member to appropriate teams and roles:
   - **Role in the organization**:
     - Select **Member** for normal users (can see all members and be granted access to repositories)
     - Select **Owner** for admin users (full administrative rights to the organization)
   - **Teams**: Select the teams this member should belong to (e.g., cpu, gpu, official)
   - Click **Send invitation**

   ![Role and Team Assignment](../_static/images/github-7.png)

5. Repeat this process for all members you want to add to your organization

## Step 4: Create a GitHub App

:::{note}
GitHub Apps are the recommended way to integrate with GitHub. They are created under the organization (not a personal account), support fine-grained permissions, and enable private repository access for users.
:::

1. Go to your organization's GitHub App creation page:
   `https://github.com/organizations/<your-organization>/settings/apps/new`

2. Fill in the basic information:
   - **GitHub App name**: A unique name (e.g., "auplc-hub")
   - **Homepage URL**: Your JupyterHub URL (e.g., `https://your.domain.com`)
   - **Callback URL**: Your OAuth callback URL
     - Single auth: `https://<your-domain>/hub/oauth_callback`
     - Multi auth: `https://<your-domain>/hub/github/oauth_callback`
   - **Expire user authorization tokens**: Check (recommended)
   - **Request user authorization (OAuth) during installation**: Check
   - **Webhook -> Active**: Uncheck (not needed)

3. Set permissions:
   - **Repository permissions**:
      - `Contents`: Read-only (for cloning private repos)
      - `Metadata`: Read-only (selected by default)
   - **Organization permissions**:
      - `Members`: Read-only (required for team-based resource access control and group sync)

   :::{important}
   `Members: Read-only` is required for the Hub's platform-owned team synchronization. Without this organization permission, the Hub cannot list organization teams or team members and logs errors such as `Resource not accessible by integration` when calling the GitHub GraphQL API.
   :::

4. Installation scope:
   - **Where can this GitHub App be installed?**: Any account
   - Click **Create GitHub App**

5. After creation, note down the following:
    - **Client ID**: Displayed on the App's General page (e.g., `Iv23liXXXXXX`)
    - **Client secret**: Click **Generate a new client secret** -- copy it immediately
    - **App ID**: Displayed on the App's General page. This is different from the Client ID.
    - **App slug**: The URL-safe name in the App's URL (e.g., `auplc-hub`)

6. Generate a private key:
   - On the App's General page, click **Generate a private key**.
   - Store the downloaded `.pem` file as a Kubernetes secret or mount it into the Hub pod by your deployment's secret-management process.
   - Record the mounted file path. You will use it as `hub.config.GitHubOAuthenticator.private_key_file`.

7. Install the GitHub App on the organization:
   - Open the App's **Install App** page.
   - Install it on the same organization configured as `custom.githubOrgName`.
   - Select the repositories users may access if private repository cloning is enabled.
   - If you later add or change permissions, an organization owner must approve the updated installation permissions.

   `installation_id` does not normally need to be configured manually. The Hub can discover it from the organization installation with `GET /orgs/{org}/installation` as long as the app is installed on that organization.

## Step 5: Configure JupyterHub

1. Open your deployment configuration file (`runtime/values.yaml` or environment-specific override)

2. Add the GitHub App configuration:

   ```yaml
   custom:
     githubOrgName: "<YOUR-ORG-NAME>"

     gitClone:
        githubAppName: "your-app-slug"  # Enables private repo access & repo picker

   hub:
     config:
       GitHubOAuthenticator:
         oauth_callback_url: "https://<Your.domain>/hub/github/oauth_callback"
         app_id: "<GitHub App App ID>"
         installation_id: ""  # Optional; leave blank to auto-discover from the org installation
         private_key_file: "/path/to/mounted/github-app-private-key.pem"
         # private_key: ""  # Alternative to private_key_file; prefer mounted secrets for production
         team_sync_ttl_seconds: 3600
         client_id: "<GitHub App Client ID>"
         client_secret: "<GitHub App Client Secret>"
         allowed_organizations:
           - <YOUR-ORG-NAME>
         scope: []  # GitHub App uses App-level permissions, not OAuth scopes
   ```

    :::{note}
    `scope: []` is correct for GitHub Apps. Permissions (Contents, Members, etc.) are configured in the App settings on GitHub, not via OAuth scopes.
    :::

   :::{tip}
   The Hub uses the GitHub App installation token for server-to-server team synchronization. It first lists actual organization teams, intersects them with `custom.teams.mapping`, and then batches team member lookups through GitHub GraphQL. This avoids per-user OAuth token lookups and reduces GitHub API traffic. If a configured team no longer exists on GitHub, it is logged and skipped instead of failing the entire sync.
   :::

   :::{warning}
   The GitHub App must still be installed on the organization. Leaving `installation_id` blank only skips manual ID entry; it does not remove the installation requirement.
   :::

3. Configure team-to-resource mapping in `values.yaml`:

   ```yaml
   custom:
     teams:
       mapping:
         cpu:
           - cpu
         gpu:
           - Course-CV
           - Course-DL
           - Course-LLM
         official:
           - cpu
           - Course-CV
           - Course-DL
           - Course-LLM
   ```

   Team mapping keys should correspond to GitHub team names/slugs. The Hub normalizes configured keys for GitHub API lookup, for example `AUP` is queried as the GitHub team slug `aup`, while the JupyterHub group remains `AUP`.

4. Deploy:

   ```bash
   helm upgrade jupyterhub ./chart -n jupyterhub -f values.yaml
   ```

## Verification

1. Navigate to your JupyterHub URL
2. You should see a "Sign in with GitHub" button
3. Click it and authorize the application
4. You should be redirected back to JupyterHub and logged in
5. Verify that users can only access resources based on their team membership

## Troubleshooting

- **OAuth callback error**: Ensure your callback URL exactly matches what you configured in GitHub (including HTTPS)
- **Organization not found**: Verify the organization name in your configuration matches your GitHub organization exactly
- **Users can't access resources**: Check that users are added to the correct teams in GitHub
- **Team sync fails with `Resource not accessible by integration`**: Ensure the GitHub App installation on your organization has `Members: Read-only` under Organization permissions. If you changed permissions after installing the app, an organization owner must approve the updated permissions on the installed app.
- **Configured team is skipped**: Verify the team exists in the GitHub organization. The Hub lists actual GitHub teams first and only syncs teams that exist.
- **Installation token unavailable**: Verify `app_id` and `private_key_file` are configured and that the GitHub App is installed on `custom.githubOrgName`. `installation_id` can usually remain blank.
- **Authentication fails**: Verify your Client ID and Client Secret are correct and the secret hasn't expired

## Migrating from OAuth App to GitHub App

If you are currently using a legacy GitHub OAuth App, follow these steps to migrate.

### Why Migrate?

| | OAuth App | GitHub App |
|---|---|---|
| **Ownership** | Personal account only | Organization-level |
| **Permissions** | Coarse OAuth scopes (`repo` = full read/write to ALL repos) | Fine-grained per-permission (e.g. Contents: read-only) |
| **Private repo access** | Requires `repo` scope (overly broad) | Per-repo authorization by user |
| **Staff changes** | App lost if owner leaves | Org admins retain control |

### Migration Steps

1. **Create a GitHub App** under your organization (see Step 4 above)

2. **Update `values.yaml`** -- change the OAuth credentials and add GitHub App server-to-server settings:

   ```yaml
   custom:
     githubOrgName: "<YOUR-ORG-NAME>"

     gitClone:
        githubAppName: "your-app-slug"          # NEW -- add this

   hub:
     config:
       GitHubOAuthenticator:
         app_id: "<GitHub App App ID>"           # NEW -- App ID, not Client ID
         installation_id: ""                     # NEW -- optional; auto-discovered from org installation
         private_key_file: "/path/to/mounted/github-app-private-key.pem"  # NEW
         team_sync_ttl_seconds: 3600             # NEW -- cache/throttle team sync
         client_id: "<GitHub App Client ID>"    # CHANGE -- from OAuth App's ID
         client_secret: "<GitHub App Client Secret>"  # CHANGE -- from OAuth App's secret
         scope: []                               # CHANGE -- was [read:user, read:org]
         # allowed_organizations, oauth_callback_url -- keep unchanged
   ```

3. **Deploy**:

   ```bash
   helm upgrade jupyterhub ./chart -n jupyterhub -f values.yaml
   ```

4. **User impact**:
   - Existing logged-in sessions continue to work
   - On next login, users go through the new GitHub App OAuth flow (same experience)
   - Users who want private repo access can authorize repos on the spawn page

5. **Clean up**: Once all users have re-logged, delete the old OAuth App from GitHub (Settings -> Developer settings -> OAuth Apps)

## Security Best Practices

1. Always use HTTPS for your JupyterHub deployment
2. Keep your Client Secret secure and never commit it to version control
3. Regularly review organization members and their team assignments
4. Use environment variables or secret management systems for storing OAuth credentials
5. Create the GitHub App under the organization (not a personal account) so it survives staff changes
6. Set minimal App permissions -- Contents (read-only) and Members (read-only) are sufficient

## Additional Resources

- [JupyterHub Documentation](https://jupyterhub.readthedocs.io/)
- [GitHub Apps Documentation](https://docs.github.com/en/apps)
- [OAuthenticator Documentation](https://oauthenticator.readthedocs.io/)
