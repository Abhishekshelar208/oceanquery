import '../models/argo_statistics.dart';
import 'api/api_client.dart';

class ArgoService {
  static final ArgoService _instance = ArgoService._internal();
  factory ArgoService() => _instance;
  ArgoService._internal();

  final ApiClient _apiClient = ApiClient();

  /// Fetch ARGO statistics from backend
  Future<ArgoStatistics> getStatistics() async {
    try {
      final response = await _apiClient.getArgoStatistics();
      return ArgoStatistics.fromJson(response);
    } catch (e) {
      throw Exception('Failed to fetch ARGO statistics: $e');
    }
  }

  /// Fetch list of ARGO floats
  Future<List<dynamic>> getFloats({
    String? status,
    int limit = 50,
    int offset = 0,
  }) async {
    try {
      return await _apiClient.getArgoFloats(
        status: status,
        limit: limit,
        offset: offset,
      );
    } catch (e) {
      throw Exception('Failed to fetch ARGO floats: $e');
    }
  }

  /// Get health check from backend
  Future<bool> checkBackendHealth() async {
    try {
      final response = await _apiClient.healthCheck();
      return response['status'] == 'healthy' || response.containsKey('status');
    } catch (e) {
      return false;
    }
  }

  /// Get measurement summary statistics
  Future<Map<String, dynamic>> getMeasurementSummary() async {
    try {
      return await _apiClient.getMeasurementSummary();
    } catch (e) {
      throw Exception('Failed to fetch measurement summary: $e');
    }
  }

  /// Get measurement statistics for a parameter
  Future<List<dynamic>> getMeasurementStats({
    String? profileId,
    String parameter = 'temperature',
  }) async {
    try {
      return await _apiClient.getMeasurementStats(
        profileId: profileId,
        parameter: parameter,
      );
    } catch (e) {
      throw Exception('Failed to fetch measurement stats: $e');
    }
  }

  /// Get complete profile data
  Future<Map<String, dynamic>> getProfileData(String profileId) async {
    try {
      return await _apiClient.getProfileData(profileId);
    } catch (e) {
      throw Exception('Failed to fetch profile data: $e');
    }
  }

  /// Get profile plot as base64 image
  Future<Map<String, dynamic>> getProfilePlot(
    String profileId, {
    String plotType = 'temperature',
    int width = 10,
    int height = 8,
  }) async {
    try {
      return await _apiClient.getProfilePlot(
        profileId,
        plotType: plotType,
        width: width,
        height: height,
      );
    } catch (e) {
      throw Exception('Failed to fetch profile plot: $e');
    }
  }
}
