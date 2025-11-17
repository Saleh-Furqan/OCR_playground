# 4. Frontend Implementation

The frontend is built as a single-page application using React 19.0 which provides a component-based architecture for building interactive user interfaces. The application structure follows React best practices with clear separation between pages, reusable components, and utility functions.

## 4.1 Application Structure

The main.tsx file serves as the entry point creating the root React element and rendering the App component into the DOM. React Router DOM wraps the application providing client-side routing capabilities allowing navigation between different views without full page reloads. The App.tsx file defines all routes mapping URL paths to page components including the home page at the root path, upload page at /upload, receipts listing page at /receipts, receipt detail page at /receipt/:deviceId/:receiptId using URL parameters, settings page at /settings, about page at /about, and contact page at /contact.

Components are organized into two categories: pages that represent full screens and are mapped to routes, and components that are reusable UI elements composed within pages. The pages directory contains components like HomePage which displays the landing page with the ReTouch value proposition, UploadPage which provides the receipt upload interface, ReceiptsPage which lists all receipts for the authenticated device, and ReceiptDetailPage which shows a single receipt with viewing and sharing options. The components directory contains smaller reusable elements including Navigation which renders the top navigation bar present on all pages, ReceiptUpload which encapsulates the file upload form logic, and ReceiptViewer which handles displaying receipt images with loading states.

## 4.2 Key Components

The ReceiptUpload component manages the file upload workflow using React's useState hook to track the selected file and upload progress. When a user selects a file using the file input element, the onChange handler stores the file in component state. When the user clicks the upload button, the component constructs a FormData object containing the file and metadata, makes a POST request to the /api/receipt endpoint using the fetch API, and displays success or error messages based on the response. The component also validates file types ensuring only images and PDFs are accepted, and enforces a maximum file size of 10MB to prevent excessive bandwidth usage and S3 costs.

The ReceiptViewer component accepts a receipt URI in the format device_id/receipt_id and handles fetching and displaying the receipt image. It uses the useState hook to track loading state and the receipt data, and the useEffect hook to trigger data fetching when the component mounts or the receipt URI changes. The component first parses the URI to extract device ID and receipt ID, makes a GET request to /api/receipt with these parameters, extracts the presigned URL from the response, and sets it as the src attribute of an img element. While loading, the component displays a spinner or skeleton screen providing visual feedback that content is being retrieved. If an error occurs, the component displays an appropriate error message instead of the image.

The ReceiptDetailPage component uses React Router's useParams hook to extract deviceId and receiptId from the URL path. It then passes these to the ReceiptViewer component and also provides additional UI elements including a download button that triggers a file download by opening the presigned URL in a new tab with the download attribute, a share button that copies the receipt URL to the clipboard allowing users to share receipts with others, and a delete button that calls the DELETE /api/receipt endpoint and navigates back to the receipts list on successful deletion.

The Navigation component renders a horizontal navigation bar with links to all major pages using React Router's Link component. These links enable client-side navigation where clicking a link updates the URL and renders the appropriate page component without requesting a new HTML document from the server. The Navigation component also displays the ReTouch logo and conditionally shows user-specific elements like device ID if authentication state is available.

## 4.3 State Management

The application uses React's built-in state management through hooks rather than external libraries like Redux or MobX. The useState hook provides local component state for data that only affects a single component such as form input values, loading indicators, and error messages. The useEffect hook handles side effects including API calls, subscriptions, and DOM manipulations that occur in response to state or prop changes.

For data that needs to be shared across multiple components, the application uses prop drilling passing data from parent to child components through props. While this can lead to deeply nested prop passing, the relatively shallow component hierarchy of ReTouch makes this approach manageable without requiring context API or state management libraries. Future expansion to more complex state requirements may motivate adoption of Zustand or Redux Toolkit for centralized state management.

## 4.4 API Integration

Frontend code interacts with the backend API using the browser's fetch API which provides a promise-based interface for making HTTP requests. API calls are wrapped in async functions using async/await syntax for cleaner error handling compared to promise chains. Each API function constructs the appropriate request including URL with query parameters for GET requests, request body with JSON or FormData for POST and PUT requests, and headers including Content-Type and any authentication tokens.

The frontend retrieves the client certificate from the browser's certificate store where it was installed after being issued by the ReTouch Certificate Authority. When making requests to API endpoints that require authentication, the browser automatically includes this certificate in the TLS handshake. The application does not need to manually attach the certificate as this is handled transparently by the browser's networking stack. The nginx reverse proxy verifies the certificate and either allows the request to proceed or returns a 403 Forbidden response before reaching the backend.

Error handling wraps fetch calls in try-catch blocks to handle network errors and uses response.ok to check for HTTP error status codes. When an error occurs, the application displays user-friendly error messages rather than raw error details, and logs errors to the browser console for debugging. Specific error codes like 404 Not Found or 403 Forbidden trigger appropriate UI states such as showing "Receipt not found" or "Access denied" messages.

## 4.5 Styling

The application uses standard CSS for styling with styles defined in CSS files imported into components. The main App.css file contains global styles including CSS custom properties for colors allowing consistent theming across the application, typography settings for font families and sizes, and responsive breakpoints for mobile and tablet layouts. Component-specific styles are defined in separate CSS files co-located with components following the pattern ComponentName.css.

The styling follows a mobile-first approach where base styles are optimized for small screens and media queries add enhancements for larger screens. Flexbox and CSS Grid provide responsive layouts that adapt to different screen sizes without requiring separate mobile and desktop versions. The navigation bar collapses into a hamburger menu on small screens, the receipt grid adjusts the number of columns based on available width, and text sizes and spacing scale proportionally using relative units like rem and em.

The ReTouch branding elements including logo, color scheme, and typography are applied consistently throughout the application. The primary brand color is used for interactive elements like buttons and links, creating a cohesive visual identity. Hover and focus states provide visual feedback for interactive elements improving usability.

## 4.6 Build and Deployment

The production build process uses Vite to compile and optimize the application. Running npm run build executes Vite's build command which transpiles TypeScript to JavaScript, bundles all modules into optimized chunks with code splitting at dynamic import boundaries, minifies JavaScript and CSS removing whitespace and shortening variable names, and outputs all files to the dist directory. The resulting build includes index.html as the entry point, JavaScript bundle files with content-based hash names for cache busting, CSS files also with hashed names, and static assets in the public directory.

The Dockerfile for the frontend uses a multi-stage build starting with a Node.js image to run the build process. The first stage copies package.json and package-lock.json, runs npm install to download dependencies, copies source files, and runs npm run build to create the production bundle. The second stage uses nginx Alpine as the base image providing a minimal web server, copies only the dist directory from the first stage, and configures nginx to serve the static files. This multi-stage approach ensures the final image contains only the built application without development dependencies or build tools, resulting in an image size under 50MB compared to over 500MB if the entire Node.js build environment were included.

# 5. Infrastructure and DevOps

## 5.1 Docker Containerization

Each service in the ReTouch architecture runs in its own Docker container providing isolation, reproducibility, and portability. The backend service uses a Python 3.11 Alpine base image chosen for its small size and security updates. The Dockerfile installs system dependencies required by Python packages including PostgreSQL client libraries for psycopg2 and build tools for native extensions, copies requirements.txt and installs Python packages using pip, and copies application code into the container. The container runs Gunicorn as the main process with appropriate worker configuration.

The frontend container uses a two-stage build as described previously. The development container runs the Vite dev server for hot module replacement during development, while the production container serves pre-built static files through nginx. This flexibility allows developers to iterate quickly with instant feedback during development while still deploying optimized assets to production.

The Certificate Authority service follows a similar pattern to the backend using Python and Flask. It has its own Dockerfile and requirements.txt separate from the main backend allowing independent dependency management and deployment. The CA service is deployed as a separate container on port 5001 with its own database ensuring complete isolation from the main application.

PostgreSQL databases run in official PostgreSQL 16 Alpine containers. The docker-compose.yml file configures persistent volumes mounted at /var/lib/postgresql/data ensuring database files survive container restarts. Environment variables configure database names, usernames, and passwords. Initialization scripts in the postgres_scripts directory create required database schemas and seed initial data when the database first starts.

## 5.2 Docker Compose Orchestration

Docker Compose orchestrates the multi-container application defining services, networks, and volumes in docker-compose.yml. The file defines six services including the main PostgreSQL database, backend application, frontend application, Certificate Authority database, CA application, and nginx reverse proxy. Dependencies between services are declared using depends_on ensuring containers start in the correct order. The postgres service must start before backend since the backend connects to PostgreSQL on startup. The backend must start before nginx since nginx proxies requests to the backend.

Networks isolate container communication with a custom bridge network allowing containers to resolve each other by service name. The backend connects to PostgreSQL using the hostname postgres which Docker DNS resolves to the container's IP address. This eliminates hardcoded IP addresses and makes the configuration portable across different environments.

Volumes provide persistent storage for databases and uploaded files. The postgres_data volume stores PostgreSQL data files ensuring receipts and device records persist when containers restart. The uploads volume stores receipt files uploaded directly to the backend rather than S3 in development mode. Named volumes are managed by Docker and stored in a system-specific location, avoiding permission issues that occur with bind mounts on some systems.

The docker-compose.yml file supports multiple profiles allowing selective service startup. The default profile starts all production services. The debug-backend profile runs the backend with additional logging and without Gunicorn for easier debugging. The debug-ca profile does the same for the Certificate Authority. Developers can start specific profiles using docker-compose --profile debug-backend up to work on just the backend without starting the full stack.

## 5.3 Nginx Configuration

The nginx configuration in nginx/nginx.conf implements the reverse proxy and SSL termination functionality. The http block defines upstream servers for backend and CA services using their Docker Compose service names as hostnames. Upstream blocks enable load balancing if multiple backend containers run, although currently only single instances are configured.

The server block for port 443 handles HTTPS traffic. SSL configuration specifies certificate and private key file paths, enables TLS 1.2 and 1.3 protocols, and configures cipher suites prioritizing forward secrecy and strong encryption. The ssl_client_certificate directive specifies the CA bundle file containing the ReTouch CA's public certificate, and ssl_verify_client optional enables client certificate verification for specific locations while allowing unauthenticated access to others.

Location blocks define routing rules. The location /api block proxies requests to the backend upstream and requires client certificate verification by checking the $ssl_client_verify variable equals SUCCESS. If verification fails, a 403 Forbidden response is returned. The proxy_pass directive forwards requests to the backend adding X-Real-IP and X-Forwarded-For headers so the backend can access the client's IP address. The location /certmanage block proxies to the CA service without client certificate requirements since users accessing this portal to obtain certificates obviously do not have certificates yet.

The location / block serves static files directly from the filesystem using the root directive pointing to the directory containing built frontend assets. The try_files directive implements fallback routing for single-page applications. When a request arrives, nginx first checks if a file matching the requested path exists. If not, it checks if a directory exists. If neither exists, it serves index.html allowing React Router to handle the route. This ensures deep links into the SPA work correctly when users bookmark or share URLs.

Rate limiting configuration defines limit_req_zone directives creating shared memory zones that track request rates per client IP. The api zone limits API requests to 300 per minute preventing abuse while allowing normal usage. The certmanage zone limits CA portal requests to 30 per minute since certificate issuance should be infrequent. The limit_req directive applies these zones to specific locations with burst parameters allowing short-term traffic spikes without rejecting legitimate requests.

Security headers are added to all responses including X-Frame-Options DENY preventing the application from being embedded in iframes to defend against clickjacking attacks, X-Content-Type-Options nosniff preventing MIME type sniffing that could lead to XSS attacks, and X-XSS-Protection enabling browser XSS filters as an additional defense layer. The add_header directives in the server block apply these headers to all responses.

## 5.4 SSL and TLS Configuration

SSL certificates for the production domain are obtained from Let's Encrypt using the Certbot tool. Let's Encrypt is a free certificate authority that issues domain-validated certificates valid for 90 days. Certbot automates the certificate request, validation, and renewal process. The HTTP-01 challenge method proves domain ownership by serving a file at a specific URL. Certbot places the challenge file in the webroot, Let's Encrypt requests it via HTTP, and upon successful validation issues the certificate.

Certificate renewal is automated using a cron job that runs Certbot periodically checking if certificates are due for renewal. Certbot renews certificates when they have less than 30 days remaining validity ensuring ample time to detect and resolve renewal failures before certificates expire. After successful renewal, nginx is reloaded using certbot --post-hook to pick up the new certificates without downtime.

The ReTouch Certificate Authority issues client certificates to devices enabling mutual TLS authentication. The CA is implemented as a Flask application using the cryptography library to generate certificates. Users access the CA portal at /certmanage, authenticate using username and password, and submit a Certificate Signing Request containing their public key. The CA validates the request, generates a certificate signed with the CA's private key, and returns it to the user for installation in their browser or device.

The CA maintains a database of issued certificates tracking serial numbers and expiration dates. Certificate revocation is supported through a simple status field, although full Certificate Revocation List or OCSP implementation is deferred to future work. The CA's own certificate is generated once during initial setup and configured in nginx as the trusted CA bundle. Only certificates signed by this CA are accepted for API authentication.

## 5.5 Deployment Process

Production deployment to AWS follows a documented process ensuring reliable updates. The process begins with running tests locally using pytest to verify all unit and integration tests pass. Code is then committed to version control and pushed to the repository. On the production EC2 instance, the repository is pulled to get the latest code changes. Environment variables are reviewed and updated if necessary ensuring sensitive values like database passwords and AWS keys are correctly configured.

Docker images are built using docker-compose build which creates images for all services that have build configurations in the compose file. Building on the production instance rather than using a registry simplifies the deployment pipeline although using Amazon ECR or Docker Hub would be more appropriate for a team environment. The build process takes several minutes as it installs dependencies and compiles assets.

After building images, running docker-compose down stops and removes existing containers ensuring a clean slate. Database volumes are not removed so data persists across deployments. Running docker-compose up -d starts all services in detached mode returning the terminal immediately while containers run in the background. The depends_on directives ensure services start in the correct order although additional health checks using wait-for-it.sh scripts verify services are actually ready to accept connections before dependent services try to connect.

After startup, docker-compose logs is used to verify all services started successfully without errors. The logs are monitored for a few minutes to catch any immediate issues. The production website is then accessed through a browser to perform smoke testing including verifying the homepage loads, testing file upload functionality, checking that receipts can be viewed, and confirming the Certificate Authority portal is accessible.

If issues are detected, docker-compose logs can be used to investigate specific services. Common issues include database connection failures when PostgreSQL is slow to start which are resolved by restarting the affected service, permission errors with volume mounts which require adjusting ownership of Docker volumes, and missing environment variables which are added to docker-compose.yml and containers restarted. The previous images remain available allowing quick rollback by stopping containers and starting the previous version if necessary.
