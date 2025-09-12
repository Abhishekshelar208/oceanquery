import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:logger/logger.dart';

class ApiClient {
  static final ApiClient _instance = ApiClient._internal();
  factory ApiClient() => _instance;
  ApiClient._internal();

  String? _baseUrl;
  Logger? _logger;
  String? _authToken;
  bool _initialized = false;

  void initialize() {
    if (_initialized) return; // Prevent multiple initialization
    
    _baseUrl = dotenv.env['API_BASE_URL'] ?? 'http://localhost:8000';
    _logger = Logger();
    _logger!.i('API Client initialized with base URL: $_baseUrl');
    _initialized = true;
  }
  
  String get baseUrl {
    if (_baseUrl == null) {
      initialize();
    }
    return _baseUrl!;
  }
  
  Logger get logger {
    if (_logger == null) {
      initialize();
    }
    return _logger!;
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
        Uri.parse('$baseUrl/api/v1/chat/query'),
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
      logger.e('Error sending chat message: $e');
      rethrow;
    }
  }

  // Advanced Chat with RAG enhancement
  Future<Map<String, dynamic>> sendAdvancedChatMessage(String message) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/v1/enhanced/chat'),
        headers: _headers,
        body: jsonEncode({
          'query': message,
          'enable_rag': true,
          'include_sql': false,
          'max_results': 100,
        }),
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw ApiException('Failed to send advanced chat message: ${response.statusCode}');
      }
    } catch (e) {
      logger.e('Error sending advanced chat message: $e');
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

      final uri = Uri.parse('$baseUrl/api/v1/argo-real/floats')
          .replace(queryParameters: queryParams);

      final response = await http.get(uri, headers: _headers);

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw ApiException('Failed to get ARGO floats: ${response.statusCode}');
      }
    } catch (e) {
      logger.e('Error getting ARGO floats: $e');
      rethrow;
    }
  }

  // Alternative method name for convenience
  Future<List<dynamic>> getFloats({
    String? status,
    int limit = 50,
    int offset = 0,
  }) async {
    return getArgoFloats(status: status, limit: limit, offset: offset);
  }

  Future<Map<String, dynamic>> getArgoStatistics() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/v1/argo/statistics'),
        headers: _headers,
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw ApiException('Failed to get ARGO statistics: ${response.statusCode}');
      }
    } catch (e) {
      logger.e('Error getting ARGO statistics: $e');
      rethrow;
    }
  }

  // Authentication endpoints
  Future<Map<String, dynamic>> login(String email, String password) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/v1/auth/login'),
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
      logger.e('Error logging in: $e');
      rethrow;
    }
  }

  Future<Map<String, dynamic>> demoLogin() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/v1/auth/demo-login'),
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
      logger.e('Error with demo login: $e');
      rethrow;
    }
  }

  // Health check
  Future<Map<String, dynamic>> healthCheck() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/health'),
        headers: _headers,
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw ApiException('Health check failed: ${response.statusCode}');
      }
    } catch (e) {
      logger.e('Error checking health: $e');
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
        Uri.parse('$baseUrl/api/v1/export/request'),
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
      logger.e('Error requesting export: $e');
      rethrow;
    }
  }

  Future<List<dynamic>> getExportJobs() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/v1/export/jobs'),
        headers: _headers,
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw ApiException('Failed to get export jobs: ${response.statusCode}');
      }
    } catch (e) {
      logger.e('Error getting export jobs: $e');
      rethrow;
    }
  }

  // Measurement endpoints
  Future<Map<String, dynamic>> getMeasurementSummary() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/v1/measurements/summary'),
        headers: _headers,
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw ApiException('Failed to get measurement summary: ${response.statusCode}');
      }
    } catch (e) {
      logger.e('Error getting measurement summary: $e');
      rethrow;
    }
  }

  Future<List<dynamic>> getMeasurementStats({
    String? profileId,
    String parameter = 'temperature',
  }) async {
    try {
      final queryParams = {
        'parameter': parameter,
        if (profileId != null) 'profile_id': profileId,
      };

      final uri = Uri.parse('$baseUrl/api/v1/measurements/stats')
          .replace(queryParameters: queryParams);

      final response = await http.get(uri, headers: _headers);

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw ApiException('Failed to get measurement stats: ${response.statusCode}');
      }
    } catch (e) {
      logger.e('Error getting measurement stats: $e');
      rethrow;
    }
  }

  Future<Map<String, dynamic>> getProfileData(String profileId) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/v1/measurements/profile/$profileId'),
        headers: _headers,
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw ApiException('Failed to get profile data: ${response.statusCode}');
      }
    } catch (e) {
      logger.e('Error getting profile data: $e');
      rethrow;
    }
  }

  Future<Map<String, dynamic>> getProfilePlot(
    String profileId, {
    String plotType = 'temperature',
    int width = 10,
    int height = 8,
  }) async {
    try {
      final queryParams = {
        'plot_type': plotType,
        'width': width.toString(),
        'height': height.toString(),
      };

      final uri = Uri.parse('$baseUrl/api/v1/measurements/plot/$profileId')
          .replace(queryParameters: queryParams);

      final response = await http.get(uri, headers: _headers);

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw ApiException('Failed to get profile plot: ${response.statusCode}');
      }
    } catch (e) {
      logger.e('Error getting profile plot: $e');
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
