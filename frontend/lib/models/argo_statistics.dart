class ArgoStatistics {
  final int totalFloats;
  final int activeFloats;
  final int totalProfiles;
  final Coverage coverage;
  final List<String> parametersAvailable;
  final DataQuality dataQuality;
  final String lastUpdated;

  ArgoStatistics({
    required this.totalFloats,
    required this.activeFloats,
    required this.totalProfiles,
    required this.coverage,
    required this.parametersAvailable,
    required this.dataQuality,
    required this.lastUpdated,
  });

  factory ArgoStatistics.fromJson(Map<String, dynamic> json) {
    return ArgoStatistics(
      totalFloats: json['total_floats'] ?? 0,
      activeFloats: json['active_floats'] ?? 0,
      totalProfiles: json['total_profiles'] ?? 0,
      coverage: Coverage.fromJson(json['coverage'] ?? {}),
      parametersAvailable: List<String>.from(json['parameters_available'] ?? []),
      dataQuality: DataQuality.fromJson(json['data_quality'] ?? {}),
      lastUpdated: json['last_updated'] ?? '',
    );
  }

  // Calculate derived metrics
  int get inactiveFloats => totalFloats - activeFloats;
  double get activeFloatsPercentage => totalFloats > 0 ? (activeFloats / totalFloats) * 100 : 0;
  double get dataQualityPercentage => dataQuality.totalGoodProfiles > 0 
      ? (dataQuality.goodProfiles / dataQuality.totalGoodProfiles) * 100 
      : 0;
}

class Coverage {
  final GeographicBounds geographicBounds;
  final TemporalRange temporalRange;
  final DepthRange depthRange;

  Coverage({
    required this.geographicBounds,
    required this.temporalRange,
    required this.depthRange,
  });

  factory Coverage.fromJson(Map<String, dynamic> json) {
    return Coverage(
      geographicBounds: GeographicBounds.fromJson(json['geographic_bounds'] ?? {}),
      temporalRange: TemporalRange.fromJson(json['temporal_range'] ?? {}),
      depthRange: DepthRange.fromJson(json['depth_range'] ?? {}),
    );
  }
}

class GeographicBounds {
  final double minLat;
  final double maxLat;
  final double minLon;
  final double maxLon;

  GeographicBounds({
    required this.minLat,
    required this.maxLat,
    required this.minLon,
    required this.maxLon,
  });

  factory GeographicBounds.fromJson(Map<String, dynamic> json) {
    return GeographicBounds(
      minLat: (json['min_lat'] ?? 0).toDouble(),
      maxLat: (json['max_lat'] ?? 0).toDouble(),
      minLon: (json['min_lon'] ?? 0).toDouble(),
      maxLon: (json['max_lon'] ?? 0).toDouble(),
    );
  }

  // Calculate coverage area percentage (simplified)
  double get coveragePercentage {
    final latRange = (maxLat - minLat).abs();
    final lonRange = (maxLon - minLon).abs();
    final totalArea = latRange * lonRange;
    final maxPossibleArea = 180.0 * 360.0; // Full globe
    return (totalArea / maxPossibleArea) * 100;
  }
}

class TemporalRange {
  final String startDate;
  final String endDate;

  TemporalRange({
    required this.startDate,
    required this.endDate,
  });

  factory TemporalRange.fromJson(Map<String, dynamic> json) {
    return TemporalRange(
      startDate: json['start_date'] ?? '',
      endDate: json['end_date'] ?? '',
    );
  }
}

class DepthRange {
  final double minDepth;
  final double maxDepth;

  DepthRange({
    required this.minDepth,
    required this.maxDepth,
  });

  factory DepthRange.fromJson(Map<String, dynamic> json) {
    return DepthRange(
      minDepth: (json['min_depth'] ?? 0).toDouble(),
      maxDepth: (json['max_depth'] ?? 0).toDouble(),
    );
  }
}

class DataQuality {
  final int goodProfiles;
  final int questionableProfiles;
  final int badProfiles;

  DataQuality({
    required this.goodProfiles,
    required this.questionableProfiles,
    required this.badProfiles,
  });

  factory DataQuality.fromJson(Map<String, dynamic> json) {
    return DataQuality(
      goodProfiles: json['good_profiles'] ?? 0,
      questionableProfiles: json['questionable_profiles'] ?? 0,
      badProfiles: json['bad_profiles'] ?? 0,
    );
  }

  int get totalGoodProfiles => goodProfiles + questionableProfiles + badProfiles;
  double get qualityPercentage => totalGoodProfiles > 0 
      ? (goodProfiles / totalGoodProfiles) * 100 
      : 0;
}
