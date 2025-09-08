import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:logger/logger.dart';

class ApiClient {
  static final ApiClient _instance = ApiClient._internal();
  factory ApiClient() => _instance;
  ApiClient._internal();

  late final String _baseUrl;
  late final Logger _logger;
  String? _authToken;

  void initialize() {
    _baseUrl = dotenv.env['API_BASE_URL'] ?? 'http://localhost:8000';
    _logger = Logger();
    _logger.i('API Client initialized with base URL: $_baseUrl');
  }

  void setAuthToken(String? token) {
    _authToken = token;
  }

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (_authToken != null) 'Authorization': 'Bearer $_authToken',
      };

  // Chat endpoints
  Future<Map<String, dynamic>> sendChatMessage(String message) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/api/v1/chat/query'),
        headers: _headers,
        body: jsonEncode({
          'message': message,
          'include_sql': true,
          'max_results': 100,
        }),
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw ApiException('Failed to send chat message: ${response.statusCode}');
      }
    } catch (e) {
      _logger.e('Error sending chat message: $e');
      rethrow;
    }
  }

  // ARGO data endpoints
  Future<List<dynamic>> getArgoFloats({
    String? status,
    int limit = 50,
    int offset = 0,
  }) async {
    try {
      final queryParams = {
        'limit': limit.toString(),
        'offset': offset.toString(),
        if (status != null) 'status': status,
      };

      final uri = Uri.parse('$_baseUrl/api/v1/argo/floats')
          .replace(queryParameters: queryParams);

      final response = await http.get(uri, headers: _headers);

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw ApiException('Failed to get ARGO floats: ${response.statusCode}');
      }
    } catch (e) {
      _logger.e('Error getting ARGO floats: $e');
      rethrow;
    }
  }

  Future<Map<String, dynamic>> getArgoStatistics() async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/api/v1/argo/statistics'),
        headers: _headers,
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw ApiException('Failed to get ARGO statistics: ${response.statusCode}');
      }
    } catch (e) {
      _logger.e('Error getting ARGO statistics: $e');
      rethrow;
    }
  }

  // Authentication endpoints
  Future<Map<String, dynamic>> login(String email, String password) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/api/v1/auth/login'),
        headers: _headers,
        body: jsonEncode({
          'email': email,
          'password': password,
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setAuthToken(data['access_token']);
        return data;
      } else {
        throw ApiException('Login failed: ${response.statusCode}');
      }
    } catch (e) {
      _logger.e('Error logging in: $e');
      rethrow;
    }
  }

  Future<Map<String, dynamic>> demoLogin() async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/api/v1/auth/demo-login'),
        headers: _headers,
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setAuthToken(data['access_token']);
        return data;
      } else {
        throw ApiException('Demo login failed: ${response.statusCode}');
      }
    } catch (e) {
      _logger.e('Error with demo login: $e');
      rethrow;
    }
  }

  // Health check
  Future<Map<String, dynamic>> healthCheck() async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/health'),
        headers: _headers,
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw ApiException('Health check failed: ${response.statusCode}');
      }
    } catch (e) {
      _logger.e('Error checking health: $e');
      rethrow;
    }
  }

  // Export endpoints
  Future<Map<String, dynamic>> requestExport({
    required String format,
    required Map<String, dynamic> queryParams,
    String? filename,
    bool includeMetadata = true,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/api/v1/export/request'),
        headers: _headers,
        body: jsonEncode({
          'format': format,
          'query_params': queryParams,
          if (filename != null) 'filename': filename,
          'include_metadata': includeMetadata,
        }),
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw ApiException('Export request failed: ${response.statusCode}');
      }
    } catch (e) {
      _logger.e('Error requesting export: $e');
      rethrow;
    }
  }

  Future<List<dynamic>> getExportJobs() async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/api/v1/export/jobs'),
        headers: _headers,
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw ApiException('Failed to get export jobs: ${response.statusCode}');
      }
    } catch (e) {
      _logger.e('Error getting export jobs: $e');
      rethrow;
    }
  }
}

class ApiException implements Exception {
  final String message;
  ApiException(this.message);

  @override
  String toString() => 'ApiException: $message';
}
