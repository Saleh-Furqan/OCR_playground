## 2.2 Technology Stack

The technology choices for ReTouch were made carefully considering factors including developer expertise, community support, performance characteristics, ecosystem maturity, and long-term maintainability. Each technology decision involved comparing multiple alternatives and selecting the option that best balanced competing concerns.

### Backend Framework Selection

Flask version 3.1.0 was chosen as the backend web framework after evaluating several Python alternatives. Flask is a micro-framework that provides essential web application functionality without imposing specific architectural patterns or requiring unnecessary components. This flexibility was crucial for ReTouch as it allowed customization of the architecture without fighting against framework conventions. Flask's minimalist approach means the application only includes components it actually needs, resulting in smaller container images and faster startup times compared to more opinionated frameworks.

Django was considered as an alternative given its comprehensive feature set including built-in admin interface, ORM, and authentication system. However, Django's monolithic architecture and many built-in components would have added unnecessary complexity for ReTouch's relatively simple data model. The admin interface provides value primarily for content-heavy applications with many models and complex relationships, but ReTouch's simple Receipt and Device models do not justify the overhead. Django's ORM, while powerful, enforces Django-specific patterns that would have made it difficult to optimize queries for ReTouch's specific access patterns. The decision to use SQLAlchemy directly with Flask provides more control and flexibility.

FastAPI was also evaluated as it provides excellent performance through asynchronous request handling and automatic API documentation generation. FastAPI's async capabilities would theoretically allow handling more concurrent requests with fewer resources. However, ReTouch's primary bottleneck is not CPU-bound request processing but rather I/O operations including database queries and S3 uploads which benefit less from async processing. The added complexity of async programming including proper management of event loops, async database drivers, and async-aware libraries was deemed not worth the marginal performance gains for ReTouch's current scale. Flask's synchronous model is simpler to understand, debug, and maintain. As traffic grows to levels where async processing becomes necessary, the system can migrate to FastAPI with minimal changes since both frameworks use similar routing and dependency injection patterns.

### API Framework

Flask-Smorest version 0.45.0 provides REST API functionality on top of Flask including automatic OpenAPI and Swagger documentation generation, request validation using Marshmallow schemas, and standardized error responses. These features significantly reduce boilerplate code compared to building REST APIs directly with Flask. Marshmallow schemas define request and response structures in declarative Python code, and Flask-Smorest automatically validates incoming requests against these schemas before route handlers execute. This ensures that handlers only process well-formed requests and moves validation logic out of business code into declarative schema definitions. The automatic OpenAPI documentation means API consumers can explore available endpoints and understand request/response formats without referring to code or separate documentation.

Flask-RESTX was considered as an alternative REST framework but Flask-Smorest was preferred for its cleaner integration with Marshmallow and better support for OpenAPI 3.0 specifications. Flask-RESTX uses its own domain-specific language for defining models which requires learning framework-specific patterns, whereas Flask-Smorest leverages Marshmallow which is widely used across the Python ecosystem and can be reused in other contexts beyond API development.

### Database and ORM

PostgreSQL version 16 Alpine serves as the primary relational database, chosen for its robustness, rich feature set, and excellent support for concurrent operations. PostgreSQL provides ACID compliance ensuring data consistency even in the face of crashes or network failures. Its MVCC architecture allows high read concurrency without readers blocking writers, which is beneficial for ReTouch's read-heavy workload where receipts are retrieved much more frequently than they are created or modified. PostgreSQL's support for UUID types was particularly relevant given ReTouch's decision to use UUIDs as primary keys for receipts, allowing the database to natively store and index these identifiers efficiently.

MySQL was considered as an alternative given its widespread use and slightly simpler administration. However, PostgreSQL's superior support for complex queries and better handling of concurrent writes made it more suitable for future expansion including analytical queries across receipt data. PostgreSQL's extensibility through extensions like pg_trgm for full-text search and PostGIS for potential location-based features provides flexibility for future enhancements without changing database systems.

SQLAlchemy version 2.0.41 provides object-relational mapping translating Python objects to database rows and vice versa. SQLAlchemy's declarative base allows defining models as Python classes with typed attributes, and the ORM automatically generates appropriate SQL queries for common operations. This abstraction reduces the amount of raw SQL code developers must write and maintain, and makes the code more portable across different database engines if needed. SQLAlchemy's session management handles connection pooling and transaction boundaries, ensuring efficient database resource usage and proper rollback behavior when errors occur.

### AWS Services

AWS S3 provides scalable object storage for receipt files with integration through boto3 version 1.37.8. S3 was chosen over other object storage solutions for its maturity, durability guarantees, and seamless integration with other AWS services used in production deployment. S3's eleven nines of durability comes from redundant storage across multiple availability zones with automatic data replication and checksumming to detect corruption. The pay-per-use pricing model means ReTouch only pays for actual storage consumed rather than provisioning fixed capacity upfront.

The presigned URL feature was particularly important for the architecture as it allows clients to upload and download files directly to and from S3 without proxying through the backend. This offloads bandwidth requirements from backend servers and reduces latency as clients communicate directly with S3's edge locations. Presigned URLs are generated by the backend using its AWS credentials and include cryptographic signatures ensuring they cannot be forged or tampered with. The configurable expiration time of one hour balances security concerns with user experience, ensuring URLs do not remain valid indefinitely while giving users sufficient time to complete download or upload operations.

Azure Blob Storage and Google Cloud Storage were considered as alternatives but AWS was selected as the primary cloud provider for its comprehensive service offerings including EC2 for compute and proven track record in the Hong Kong region where ReTouch is deployed. Using a single cloud provider simplifies billing, networking, and identity management compared to multi-cloud approaches.

### Frontend Framework

React version 19.0.0 provides the foundation for the user interface enabling component-based development and efficient re-rendering through its virtual DOM reconciliation algorithm. React's component model encourages creating reusable UI elements that encapsulate both appearance and behavior. Components like ReceiptUpload and ReceiptViewer can be composed together to build complex interfaces while remaining individually testable and maintainable. React's unidirectional data flow from parent to child components through props makes it easier to reason about how data moves through the application compared to two-way binding approaches.

Vue.js was evaluated as an alternative given its simpler learning curve and built-in state management. However, React's larger ecosystem and more extensive third-party library support made it more suitable for long-term development. React's job market presence also makes it easier to find developers with relevant experience as the team grows. Angular was considered but rejected due to its steep learning curve and heavyweight framework approach requiring TypeScript and extensive tooling configuration from the start.

### Type Safety

TypeScript version 5.7.2 adds static type checking to JavaScript enabling detection of many bugs at compile time rather than runtime. Type annotations document function signatures and object shapes making the codebase more self-documenting and easier for new developers to understand. TypeScript's structural typing allows gradually adding types to existing JavaScript code, and the strict mode catches common mistakes including null and undefined access errors, implicit any types, and incorrect function calls. IDE integration provides autocomplete and inline documentation improving developer productivity.

The decision to use TypeScript was validated early in development when type checking caught several bugs including incorrect prop types passed to React components, missing required fields in API request objects, and incorrect assumptions about nullable values. While TypeScript adds compilation overhead and requires learning additional syntax, the benefits in code quality and maintainability justified the investment.

### Build Tool

Vite version 6.2.0 serves as the build tool and development server providing extremely fast hot module replacement during development and optimized production builds. Vite leverages native ES modules in the browser during development avoiding the need to bundle code, which means changes are reflected almost instantly without full page reloads. The development server starts in milliseconds compared to seconds or minutes for traditional bundlers like Webpack, significantly improving developer experience during iterative development.

For production builds, Vite uses Rollup under the hood to create optimized bundles with code splitting, tree shaking to remove unused code, and minification to reduce file sizes. Vite automatically splits code at dynamic import boundaries allowing lazy loading of route components and reducing initial bundle size. The built React application is output to a dist directory containing index.html, JavaScript bundles, CSS files, and static assets, all optimized for production deployment.

Create React App was the de facto standard for React applications for many years but has largely been superseded by Vite due to performance advantages. Vite's architecture is fundamentally more efficient as it avoids bundling during development, whereas Create React App bundles even in development mode leading to slower iteration cycles as applications grow. The migration path from Create React App to Vite is well-documented making it easy to switch if starting with CRA.

### Routing

React Router DOM version 6.22.3 handles client-side routing allowing the single-page application to simulate multiple pages without full page reloads. Routes are defined declaratively mapping URL paths to React components, and the library handles browser history integration ensuring back and forward buttons work as users expect. The useParams and useNavigate hooks provide programmatic access to route parameters and navigation capabilities from within components.

Client-side routing required special nginx configuration using try_files to ensure all routes are served the index.html file rather than returning 404 errors for URLs that do not correspond to physical files. This configuration allows users to bookmark or share deep links to specific pages within the application and have the React Router properly render the correct component when the page loads.

### WSGI Server

Gunicorn version 23.0.0 serves as the production WSGI server running Flask applications. Flask's built-in development server is not suitable for production as it is single-threaded and lacks security hardening. Gunicorn spawns multiple worker processes to handle concurrent requests utilizing multiple CPU cores, and includes worker timeout and graceful restart capabilities for improved reliability. The configuration uses four worker processes as a starting point following the common formula of two times the number of CPU cores plus one, which provides good parallelism without excessive memory overhead from too many workers.

### Containerization

Docker provides containerization with multi-stage builds used to optimize image sizes. The frontend uses a Node.js image for building the Vite production bundle, then copies only the built dist directory into an nginx Alpine image for serving. This approach ensures the final image contains only the minimal files needed to run the application without development dependencies or build tools. Alpine Linux base images are preferred for their small size typically under 5MB compared to hundreds of megabytes for Ubuntu-based images.

Docker Compose version 2.20 orchestrates multiple containers with defined dependencies and networking. The compose file defines services including databases, backend applications, frontend server, and nginx proxy, and configures their interdependencies using depends_on directives. Volumes provide persistent storage for database data ensuring it survives container restarts. The compose file supports multiple profiles allowing developers to selectively start services such as running only the backend in debug mode without starting the entire stack.

### Reverse Proxy and Web Server

Nginx Alpine serves multiple roles as reverse proxy, SSL terminator, and static file server. As a reverse proxy, nginx forwards requests to upstream application servers while adding or modifying headers. The proxy_pass directive specifies the upstream server URL, and proxy_set_header directives add headers like X-Real-IP containing the client's IP address. As SSL terminator, nginx handles HTTPS connections and certificate verification, offloading cryptographic operations from application servers. Nginx's event-driven architecture allows it to handle thousands of concurrent connections with minimal memory using non-blocking I/O.

For static file serving, nginx is significantly more efficient than application servers. Benchmarking showed nginx serving static files at over 40,000 requests per second with sub-millisecond latency compared to under 1,000 requests per second when proxying through the Vite development server. This ten-fold performance improvement justified the architectural decision to serve static files directly from nginx rather than proxying to the frontend container in production.

Apache HTTP Server was considered as an alternative but nginx was selected for its superior performance with static files and more efficient resource usage. Nginx's configuration syntax is also more straightforward for common reverse proxy scenarios despite being less flexible than Apache's .htaccess system.

### Development Tools

Pytest provides the testing framework with fixtures for setup and teardown, parametrized tests for testing multiple input combinations, and plugins for coverage reporting. The conftest.py file defines shared fixtures available to all tests including database sessions and mock objects. ESLint version 9.17.0 enforces JavaScript and TypeScript code style preventing common mistakes and ensuring consistent formatting across the codebase. Mypy provides static type checking for Python code verifying type annotations are correct and catching type errors before runtime.
