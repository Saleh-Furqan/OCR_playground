# Appendix A: API Reference

## A.1 Receipt Management Endpoints

The ReTouch API provides RESTful endpoints for receipt management following standard HTTP conventions. All endpoints require client certificate authentication unless explicitly noted otherwise.

### POST /api/receipt

Creates a new receipt record and uploads the receipt file to AWS S3. This endpoint accepts multipart form data containing the receipt image and associated metadata.

**Request Format:** Multipart form data with the following fields. The file field contains the receipt image which must be in JPEG, PNG, or PDF format with maximum size of 10 megabytes. The device_id field contains the unique identifier for the device making the request and is extracted from the client certificate Common Name rather than being provided in the request body. The mime_type field specifies the content type of the uploaded file such as image/jpeg or application/pdf.

**Response Format:** JSON object with HTTP status 201 Created on success. The response contains receipt_id which is a UUID uniquely identifying the receipt, device_id confirming the device that owns the receipt, timestamp indicating when the receipt was created in ISO 8601 format, mime_type echoing the content type of the stored file, upload_status indicating the current status such as COMPLETED or PENDING, and optionally a presigned_url providing immediate access to view the uploaded receipt valid for one hour.

**Error Responses:** Returns 400 Bad Request if the file is missing, exceeds size limit, or has invalid format. Returns 403 Forbidden if client certificate verification fails. Returns 500 Internal Server Error if S3 upload fails or database operations encounter errors.

**Example Request:** A multipart form POST with file field containing receipt.jpg, automatically includes device_id from certificate, and Content-Type multipart/form-data boundary headers.

**Example Response:** JSON containing receipt_id such as "550e8400-e29b-41d4-a716-446655440000", device_id matching the certificate Common Name, timestamp like "2025-11-17T14:30:00Z", mime_type "image/jpeg", upload_status "COMPLETED", and presigned_url valid for 3600 seconds.

### GET /api/receipt

Retrieves metadata and generates a presigned URL for a specific receipt. This endpoint requires both device_id and receipt_id as query parameters to ensure ownership verification.

**Request Format:** GET request with query parameters device_id and receipt_id. Both parameters are required. The device_id must match the device identifier from the client certificate or the request will be rejected with 403 Forbidden.

**Response Format:** JSON object containing all receipt metadata plus a freshly generated presigned URL. Fields include receipt_id, device_id, timestamp of receipt creation, mime_type, upload_status indicating current state, and presigned_url which is a temporary URL valid for one hour allowing direct download from S3.

**Error Responses:** Returns 400 Bad Request if device_id or receipt_id parameters are missing. Returns 403 Forbidden if the device_id does not match the authenticated device or if client certificate is invalid. Returns 404 Not Found if no receipt exists with the given receipt_id for the specified device_id.

**Security Note:** The ownership verification using both device_id and receipt_id prevents enumeration attacks where an attacker might try to guess receipt IDs. Even if an attacker knows a valid receipt ID, they cannot access it without also being authenticated as the owning device.

### PUT /api/receipt

Updates the status of an existing receipt. This endpoint is primarily used for the presigned URL upload workflow where receipts are initially created with PENDING status and updated to COMPLETED after successful upload.

**Request Format:** JSON body containing device_id, receipt_id, and new_status. The new_status must be one of the UploadStatus enum values: NOT_UPLOADED, PENDING, COMPLETED, or FAILED.

**Response Format:** JSON object with the updated receipt metadata reflecting the new status.

**Error Responses:** Returns 400 Bad Request if required fields are missing or new_status is invalid. Returns 403 Forbidden if device_id does not match authenticated device. Returns 404 Not Found if receipt does not exist.

### DELETE /api/receipt

Deletes a receipt including both the database record and the S3 file. This operation is permanent and cannot be undone.

**Request Format:** GET request with query parameters device_id and receipt_id identifying the receipt to delete.

**Response Format:** Returns 204 No Content on successful deletion with empty response body.

**Error Responses:** Returns 400 Bad Request if parameters are missing. Returns 403 Forbidden if device is not authorized to delete the receipt. Returns 404 Not Found if receipt does not exist. Returns 500 Internal Server Error if deletion fails partially such as S3 deletion succeeds but database deletion fails.

**Important Note:** The deletion is not atomic across S3 and PostgreSQL. If S3 deletion succeeds but database deletion fails, the file is lost but the database record remains creating an orphaned record. Future enhancements should implement compensating transactions to handle partial failures.

### POST /api/receipt/presigned_upload

Generates a presigned URL that allows direct upload from client to S3 without proxying through the backend. This reduces backend bandwidth requirements for large receipt images.

**Request Format:** JSON body containing device_id and mime_type for the receipt to be uploaded.

**Response Format:** JSON containing receipt_id for the newly created receipt record with PENDING status, presigned_url which is a PUT URL allowing upload directly to S3 valid for one hour, and upload_fields if using POST-based presigned URLs instead of PUT.

**Client Upload Flow:** Client creates receipt record receiving presigned URL, uploads file directly to S3 using PUT request to presigned URL with Content-Type header matching mime_type, verifies upload succeeded with HTTP 200 response, and calls PUT /api/receipt to update status from PENDING to COMPLETED.

## A.2 Public Endpoints

### GET /receipt-raw/{device_id}/{receipt_id}

Provides public HTML view of receipts without requiring client certificate authentication. This enables receipt sharing with users who do not have certificates installed.

**Request Format:** GET request with device_id and receipt_id in URL path.

**Response Format:** HTML page displaying the receipt image with basic metadata. The page fetches the receipt using a backend-generated presigned URL.

**Security Consideration:** This endpoint bypasses client certificate authentication making receipts accessible to anyone who knows the URL. Users should treat receipt URLs as sensitive and avoid sharing them publicly if receipts contain confidential information.

## A.3 Certificate Authority Endpoints

The Certificate Authority service runs on port 5001 and uses session-based authentication rather than client certificates since users accessing the CA to request certificates obviously do not yet have certificates.

### POST /certmanage/login

Authenticates a user to the CA portal using username and password.

**Request Format:** JSON body or form data with username and password fields.

**Response Format:** Sets session cookie on success and returns JSON indicating successful authentication. Returns 401 Unauthorized if credentials are invalid.

### GET /certmanage/request

Displays the certificate request form where users can submit Certificate Signing Requests.

**Authentication:** Requires active session from login endpoint.

**Response Format:** HTML form allowing CSR paste or file upload.

### POST /certmanage/request

Processes a Certificate Signing Request and issues a certificate signed by the ReTouch CA.

**Request Format:** Form data or JSON containing the CSR in PEM format and optionally a device_id or Common Name for the certificate.

**Response Format:** Returns the issued certificate in PEM format along with certificate metadata including serial number, expiration date, and Common Name.

**Certificate Validity:** Issued certificates are valid for 365 days from issuance and can be renewed by submitting a new CSR before expiration.

# Appendix B: Environment Variables

## B.1 Backend Environment Variables

The backend Flask application requires the following environment variables configured in docker-compose.yml or .env files.

**DATABASE_URL:** PostgreSQL connection string in format postgresql://username:password@host:port/database. Example: postgresql://retouchuser:password123@postgres:5432/retouchdb. This variable is required for all database operations and the application will fail to start without it.

**AWS_ACCESS_KEY_ID:** AWS access key ID for S3 operations. The associated IAM user must have permissions for s3:PutObject, s3:GetObject, s3:DeleteObject on the ReTouch bucket. This variable is required for receipt upload and download functionality.

**AWS_SECRET_ACCESS_KEY:** AWS secret access key corresponding to the access key ID. This credential must be kept secure and never committed to version control. Rotation of AWS credentials requires updating this variable and restarting containers.

**AWS_REGION:** AWS region where the S3 bucket is located such as us-east-1 or ap-east-1 for Hong Kong. This must match the region where the bucket was created.

**S3_BUCKET_NAME:** Name of the S3 bucket for storing receipt files. The bucket must exist before starting the application and must be in the specified AWS region.

**FLASK_ENV:** Environment mode, either development or production. Development mode enables debug mode, auto-reloading, and detailed error pages. Production mode disables debugging and optimizes for performance.

**SECRET_KEY:** Flask secret key used for session signing and CSRF protection. This should be a long random string and must remain consistent across container restarts to prevent session invalidation. Generate using: python -c "import secrets; print(secrets.token_hex(32))".

## B.2 Certificate Authority Environment Variables

**CA_DATABASE_URL:** PostgreSQL connection string for the CA database. The CA uses a separate database from the main application for isolation.

**CA_PRIVATE_KEY_PATH:** File path to the CA private key PEM file. This file must be mounted into the container with restrictive permissions ensuring only the CA process can read it.

**CA_CERTIFICATE_PATH:** File path to the CA public certificate PEM file. This certificate is distributed to nginx and clients to enable certificate verification.

**CA_SECRET_KEY:** Flask secret key for the CA application used for session management.

## B.3 nginx Environment Variables

**SSL_CERTIFICATE_PATH:** Path to the server SSL certificate file for HTTPS. For Let's Encrypt certificates this is typically /etc/letsencrypt/live/domain/fullchain.pem.

**SSL_CERTIFICATE_KEY_PATH:** Path to the server SSL private key. For Let's Encrypt this is /etc/letsencrypt/live/domain/privkey.pem. This file must have restrictive permissions readable only by nginx.

**CLIENT_CA_BUNDLE_PATH:** Path to the CA bundle containing the ReTouch CA certificate. This enables nginx to verify client certificates. The file should contain the ReTouch CA certificate in PEM format.

## B.4 Frontend Environment Variables

**VITE_API_BASE_URL:** Base URL for API requests. In development this might be http://localhost:5000. In production this should be the public domain like https://retouchhk.com.

**VITE_CA_URL:** URL for the Certificate Authority portal used by the frontend to link users to certificate request pages.

# Appendix C: Docker Commands Reference

## C.1 Development Commands

**Start all services in development mode:**
```bash
docker-compose up
```
This starts all services with console output visible, useful for viewing logs in real-time during development.

**Start services in background:**
```bash
docker-compose up -d
```
Runs containers in detached mode returning the terminal. Use docker-compose logs to view output.

**Start specific profile:**
```bash
docker-compose --profile debug-backend up
```
Starts only services needed for backend debugging, running backend with Flask development server instead of Gunicorn.

**View logs from all services:**
```bash
docker-compose logs -f
```
Follows logs from all containers. Use --tail=100 to show only last 100 lines. Use service name to view specific service: docker-compose logs -f backend.

**Rebuild containers after code changes:**
```bash
docker-compose build
docker-compose up -d
```
Rebuilds Docker images incorporating code changes and restarts containers.

**Execute commands in running container:**
```bash
docker-compose exec backend bash
```
Opens interactive shell in the backend container. Useful for running migrations, inspecting files, or debugging.

**Run database migrations:**
```bash
docker-compose exec backend flask db upgrade
```
Applies pending database migrations. Run after pulling code with new migrations.

## C.2 Production Commands

**Stop and remove all containers:**
```bash
docker-compose down
```
Stops containers and removes them but preserves volumes and images.

**Stop and remove including volumes (CAUTION - deletes data):**
```bash
docker-compose down -v
```
Removes volumes including database data. Only use when intentionally resetting the environment.

**View resource usage:**
```bash
docker stats
```
Shows real-time CPU, memory, network, and disk I/O for running containers.

**Prune unused resources:**
```bash
docker system prune -a
```
Removes stopped containers, unused networks, dangling images, and build cache. Helpful for reclaiming disk space.

# Appendix D: Common Issues and Solutions

## D.1 Database Connection Issues

**Problem:** Backend fails to start with error "connection refused" connecting to PostgreSQL.

**Cause:** PostgreSQL container is not yet ready to accept connections when backend attempts to connect.

**Solution:** The wait-for-it.sh script should handle this but if issues persist, increase timeout in the script or manually verify PostgreSQL readiness: docker-compose exec postgres pg_isready -U retouchuser.

## D.2 Client Certificate Issues

**Problem:** API requests return 403 Forbidden despite having valid certificate installed.

**Cause:** Certificate may be expired, not properly signed by ReTouch CA, or browser not sending certificate.

**Solution:** Verify certificate validity: openssl x509 -in cert.pem -noout -dates. Verify certificate is signed by ReTouch CA: openssl verify -CAfile ca.pem cert.pem. Check nginx logs for certificate verification failures: docker-compose logs nginx | grep SSL.

## D.3 S3 Upload Failures

**Problem:** Receipt uploads fail with AWS errors.

**Cause:** Invalid AWS credentials, incorrect bucket name, insufficient IAM permissions, or network connectivity issues.

**Solution:** Verify credentials are set correctly: docker-compose exec backend env | grep AWS. Test S3 access manually: docker-compose exec backend python -c "import boto3; s3 = boto3.client('s3'); print(s3.list_buckets())". Verify IAM permissions include PutObject on the bucket.

## D.4 Static Files Not Loading

**Problem:** Frontend displays blank page or JavaScript fails to load.

**Cause:** nginx misconfigured or frontend build not copied to correct location.

**Solution:** Verify built files exist in nginx container: docker-compose exec nginx ls /usr/share/nginx/html. Check nginx logs for 404 errors: docker-compose logs nginx | grep 404. Verify nginx.conf has correct root directive.

# Appendix E: Technology Versions

## E.1 Backend Technology Stack

- Python: 3.11
- Flask: 3.1.0
- Flask-Smorest: 0.45.0
- SQLAlchemy: 2.0.41
- PostgreSQL: 16 Alpine
- Gunicorn: 23.0.0
- boto3: 1.37.8
- Werkzeug: 3.0.1
- Marshmallow: 3.22.0

## E.2 Frontend Technology Stack

- Node.js: 20.x LTS
- React: 19.0.0
- TypeScript: 5.7.2
- Vite: 6.2.0
- React Router DOM: 6.22.3
- ESLint: 9.17.0

## E.3 Infrastructure Stack

- Docker: 24.0+
- Docker Compose: 2.20+
- nginx: Alpine latest
- Let's Encrypt Certbot: 2.x
- AWS S3: API version 2006-03-01
- AWS EC2: t2.medium instance recommended

# Appendix F: Glossary

**API (Application Programming Interface):** Set of endpoints and protocols allowing programmatic interaction with ReTouch services.

**AWS (Amazon Web Services):** Cloud computing platform providing S3 storage and EC2 compute resources.

**Client Certificate:** Digital certificate installed on user devices enabling mutual TLS authentication.

**Certificate Authority (CA):** Service that issues and manages client certificates for device authentication.

**CSR (Certificate Signing Request):** Request submitted to CA containing public key and identity information.

**Docker:** Containerization platform enabling consistent deployment across environments.

**Flask:** Lightweight Python web framework used for ReTouch backend.

**Gunicorn:** WSGI HTTP server for running Flask applications in production.

**JWT (JSON Web Token):** Token-based authentication mechanism, not currently used by ReTouch which uses client certificates instead.

**Microservices:** Architectural pattern where application is composed of independently deployable services.

**Mutual TLS:** Authentication protocol where both client and server present certificates.

**nginx:** High-performance web server and reverse proxy handling SSL termination and routing.

**ORM (Object-Relational Mapping):** SQLAlchemy provides ORM translating Python objects to database tables.

**Presigned URL:** Temporary URL with embedded credentials allowing direct access to S3 objects.

**React:** JavaScript library for building user interfaces using component-based architecture.

**REST (Representational State Transfer):** Architectural style for APIs using standard HTTP methods.

**SPA (Single-Page Application):** Web application loading single HTML page and dynamically updating content.

**SQLAlchemy:** Python SQL toolkit and ORM for database interactions.

**SSL/TLS:** Cryptographic protocols providing secure communication over networks.

**UUID (Universally Unique Identifier):** 128-bit identifier used for receipt IDs ensuring global uniqueness.

**Vite:** Modern frontend build tool providing fast development server and optimized production builds.

**WSGI (Web Server Gateway Interface):** Python standard for web servers to communicate with web applications.

# Appendix G: References and Resources

## G.1 Technical Documentation

**Flask Documentation:** https://flask.palletsprojects.com/ - Comprehensive guide to Flask web framework including quickstart, API reference, and best practices.

**React Documentation:** https://react.dev/ - Official React documentation covering components, hooks, and modern patterns.

**PostgreSQL Documentation:** https://www.postgresql.org/docs/ - Complete reference for PostgreSQL database including SQL syntax, administration, and performance tuning.

**nginx Documentation:** https://nginx.org/en/docs/ - Official nginx documentation covering configuration directives, modules, and deployment.

**Docker Documentation:** https://docs.docker.com/ - Docker guides including Dockerfile reference, compose file specification, and networking.

**AWS S3 Documentation:** https://docs.aws.amazon.com/s3/ - Amazon S3 documentation covering API reference, best practices, and security.

## G.2 Research Papers and Standards

**RFC 5280:** Internet X.509 Public Key Infrastructure Certificate and Certificate Revocation List (CRL) Profile. Defines certificate format and validation.

**RFC 8446:** The Transport Layer Security (TLS) Protocol Version 1.3. Specifies TLS cryptographic protocol used for HTTPS.

**OAuth 2.0 RFC 6749:** The OAuth 2.0 Authorization Framework. Reference for future authentication enhancements.

**REST API Design:** Fielding, Roy Thomas. "Architectural Styles and the Design of Network-based Software Architectures." Doctoral dissertation, University of California, Irvine, 2000.

## G.3 OCR Research References

**SROIE Dataset:** Scanned Receipts OCR and Information Extraction dataset from ICDAR 2019 competition containing 626 annotated receipts.

**PaddleOCR Documentation:** https://github.com/PaddlePaddle/PaddleOCR - Open-source OCR toolkit documentation including PP-OCRv5 model details.

**Qwen2.5-VL Model Card:** https://huggingface.co/Qwen/Qwen2.5-VL - Vision language model documentation with usage examples.

**Document Parsing Research:** Recent papers on vision language models for document understanding from major conferences including CVPR, ECCV, and ICDAR.

## G.4 Tools and Libraries

**Postman:** API testing tool for manually testing and debugging endpoints. Collection can be exported and shared with team.

**pgAdmin:** PostgreSQL administration tool for database management, query debugging, and schema visualization.

**OpenSSL:** Toolkit for SSL/TLS protocols and certificate management, essential for testing client certificate authentication.

**Chrome DevTools:** Browser developer tools for debugging frontend issues, inspecting network requests, and profiling performance.

This appendix provides comprehensive reference material for developers, operators, and researchers working with the ReTouch platform. The combination of API documentation, configuration reference, troubleshooting guides, and external resources ensures that all necessary information for successful deployment and maintenance is readily available.
