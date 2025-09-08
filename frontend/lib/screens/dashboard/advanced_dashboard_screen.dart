import 'package:flutter/material.dart';
import '../../widgets/charts/circular_progress_chart.dart';
import '../../widgets/charts/heatmap_calendar.dart';
import '../../widgets/charts/horizontal_bar_chart.dart';
import '../../widgets/charts/mini_world_map.dart';
import '../../widgets/charts/multi_line_chart.dart';
import '../../widgets/charts/radar_chart_widget.dart';
import '../../models/argo_statistics.dart';
import '../../services/argo_service.dart';


class AdvancedDashboardScreen extends StatefulWidget {
  const AdvancedDashboardScreen({super.key});

  @override
  State<AdvancedDashboardScreen> createState() => _AdvancedDashboardScreenState();
}

class _AdvancedDashboardScreenState extends State<AdvancedDashboardScreen> {
  ArgoStatistics? _statistics;
  bool _isLoading = true;
  String? _error;
  final ArgoService _argoService = ArgoService();

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    try {
      setState(() {
        _isLoading = true;
        _error = null;
      });
      
      final statistics = await _argoService.getStatistics();
      
      setState(() {
        _statistics = statistics;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
      debugPrint('Error loading ARGO data: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Scaffold(
        backgroundColor: const Color(0xFF0A1A1A),
        body: const Center(
          child: CircularProgressIndicator(color: Colors.cyan),
        ),
      );
    }

    if (_error != null) {
      return Scaffold(
        backgroundColor: const Color(0xFF0A1A1A),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error, color: Colors.red, size: 64),
              const SizedBox(height: 16),
              Text(
                'Failed to load data',
                style: const TextStyle(color: Colors.white, fontSize: 20),
              ),
              const SizedBox(height: 8),
              Text(
                _error!,
                style: const TextStyle(color: Colors.white70, fontSize: 14),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: _loadData,
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }
    final screenWidth = MediaQuery.of(context).size.width;
    final isWideScreen = screenWidth >= 1200;
    
    return Scaffold(
      backgroundColor: const Color(0xFF0A1A1A), // Dark ocean theme
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            // Header with key metrics
            _buildHeaderMetrics(),
            const SizedBox(height: 20),
            
            // Main grid layout
            if (isWideScreen)
              _buildWideScreenLayout()
            else
              _buildNarrowScreenLayout(),
          ],
        ),
      ),
    );
  }

  Widget _buildHeaderMetrics() {
    final stats = _statistics;
    if (stats == null) return const SizedBox();
    
    // Calculate derived metrics
    final activeFloatsFormatted = _formatNumber(stats.activeFloats);
    final totalProfilesFormatted = _formatNumber(stats.totalProfiles);
    final coveragePercentage = stats.coverage.geographicBounds.coveragePercentage.toStringAsFixed(1);
    final anomaliesCount = stats.dataQuality.badProfiles + stats.dataQuality.questionableProfiles;
    
    return Row(
      children: [
        Expanded(
          child: _buildMetricCard(
            'Active Floats', 
            activeFloatsFormatted, 
            '+${((stats.activeFloatsPercentage - 85).clamp(-100, 100)).toStringAsFixed(1)}%', 
            Colors.cyan,
            Icons.sensors
          ),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: _buildMetricCard(
            'Total Profiles', 
            totalProfilesFormatted, 
            '+${((stats.totalProfiles / 20000 * 100 - 100).clamp(-100, 100)).toStringAsFixed(1)}%', 
            Colors.orange,
            Icons.analytics
          ),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: _buildMetricCard(
            'Coverage', 
            '$coveragePercentage%', 
            '+${(coveragePercentage.contains('.') ? double.parse(coveragePercentage) - 15 : 0).toStringAsFixed(1)}%', 
            Colors.green,
            Icons.public
          ),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: _buildMetricCard(
            'Poor Quality', 
            anomaliesCount.toString(), 
            '-${((anomaliesCount / stats.totalProfiles * 100 - 5).clamp(-100, 100)).toStringAsFixed(1)}%', 
            Colors.red,
            Icons.warning
          ),
        ),
      ],
    );
  }
  
  String _formatNumber(int number) {
    if (number >= 1000000) {
      return '${(number / 1000000).toStringAsFixed(1)}M';
    } else if (number >= 1000) {
      return '${(number / 1000).toStringAsFixed(1)}K';
    }
    return number.toString();
  }

  Widget _buildMetricCard(String title, String value, String change, Color color, IconData icon) {
    final isPositive = change.startsWith('+');
    
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF1A2D3A),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: color, size: 20),
              const SizedBox(width: 8),
              Text(
                title,
                style: const TextStyle(
                  color: Colors.white70,
                  fontSize: 14,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Text(
                value,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: (isPositive ? Colors.green : Colors.red).withOpacity(0.2),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  change,
                  style: TextStyle(
                    color: isPositive ? Colors.green : Colors.red,
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildWideScreenLayout() {
    return Column(
      children: [
        // Row 1: Multi-line chart + Calendar + Progress rings
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Temperature trends chart (40%)
            Expanded(
              flex: 4,
              child: _buildChartCard(
                'Temperature Trends',
                const MultiLineChart(),
                height: 300,
              ),
            ),
            const SizedBox(width: 16),
            
            // Calendar heatmap (30%)
            Expanded(
              flex: 3,
              child: _buildChartCard(
                'Data Collection Activity',
                const HeatmapCalendar(),
                height: 300,
              ),
            ),
            const SizedBox(width: 16),
            
            // Progress indicators (30%)
            Expanded(
              flex: 3,
              child: Column(
                children: [
                  _buildChartCard(
                    'Float Status',
                    CircularProgressChart(
                      percentage: _statistics?.activeFloatsPercentage ?? 0,
                      title: '${_statistics?.activeFloats ?? 0}\n${_statistics?.totalFloats ?? 0}',
                      subtitle: 'Active\nTotal',
                      color: Colors.cyan,
                    ),
                    height: 140,
                  ),
                  const SizedBox(height: 16),
                  _buildChartCard(
                    'Data Quality',
                    CircularProgressChart(
                      percentage: _statistics?.dataQuality.qualityPercentage ?? 0,
                      title: '${_statistics?.dataQuality.goodProfiles ?? 0}\n${_statistics?.dataQuality.totalGoodProfiles ?? 0}',
                      subtitle: 'Good\nTotal',
                      color: Colors.green,
                    ),
                    height: 140,
                  ),
                ],
              ),
            ),
          ],
        ),
        
        const SizedBox(height: 20),
        
        // Row 2: World map + Horizontal bars + Radar charts
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // World map with data points (40%)
            Expanded(
              flex: 4,
              child: _buildChartCard(
                'Global Float Distribution',
                const MiniWorldMap(),
                height: 350,
              ),
            ),
            const SizedBox(width: 16),
            
            // Horizontal bars (30%)
            Expanded(
              flex: 3,
              child: _buildChartCard(
                'Regional Statistics',
                const HorizontalBarChart(),
                height: 350,
              ),
            ),
            const SizedBox(width: 16),
            
            // Radar charts (30%)
            Expanded(
              flex: 3,
              child: Column(
                children: [
                  _buildChartCard(
                    'Parameter Analysis',
                    const RadarChartWidget(
                      title: 'Current',
                      values: [60, 75, 45, 60],
                    ),
                    height: 165,
                  ),
                  const SizedBox(height: 20),
                  _buildChartCard(
                    'Trend Comparison',
                    const RadarChartWidget(
                      title: 'Trend',
                      values: [80, 60, 70, 55],
                    ),
                    height: 165,
                  ),
                ],
              ),
            ),
          ],
        ),
        
        const SizedBox(height: 20),
        
        // Row 3: Additional metrics and controls
        _buildBottomMetrics(),
      ],
    );
  }

  Widget _buildNarrowScreenLayout() {
    return Column(
      children: [
        _buildChartCard(
          'Temperature Trends',
          const MultiLineChart(),
          height: 250,
        ),
        const SizedBox(height: 16),
        
        Row(
          children: [
            Expanded(
              child: _buildChartCard(
                'Float Status',
                CircularProgressChart(
                  percentage: _statistics?.activeFloatsPercentage ?? 0,
                  title: '${_statistics?.activeFloats ?? 0}\n${_statistics?.totalFloats ?? 0}',
                  subtitle: 'Active\nTotal',
                  color: Colors.cyan,
                ),
                height: 180,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: _buildChartCard(
                'Quality',
                CircularProgressChart(
                  percentage: _statistics?.dataQuality.qualityPercentage ?? 0,
                  title: '${_statistics?.dataQuality.goodProfiles ?? 0}\n${_statistics?.dataQuality.totalGoodProfiles ?? 0}',
                  subtitle: 'Good\nAll',
                  color: Colors.green,
                ),
                height: 180,
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        
        _buildChartCard(
          'Global Distribution',
          const MiniWorldMap(),
          height: 280,
        ),
        const SizedBox(height: 16),
        
        _buildChartCard(
          'Calendar Activity',
          const HeatmapCalendar(),
          height: 200,
        ),
      ],
    );
  }

  Widget _buildBottomMetrics() {
    return Row(
      children: [
        Expanded(
          child: Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: const Color(0xFF1A2D3A),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.cyan.withOpacity(0.3)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'System Health',
                  style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 16),
                _buildHealthIndicator('Database', _statistics != null ? 0.95 : 0.20, _statistics != null ? Colors.green : Colors.red),
                _buildHealthIndicator('API Response', _statistics != null ? 0.95 : 0.30, _statistics != null ? Colors.green : Colors.red),
                _buildHealthIndicator('Data Quality', (_statistics?.dataQuality.qualityPercentage ?? 0) / 100, Colors.orange),
                _buildHealthIndicator('Coverage', (_statistics?.coverage.geographicBounds.coveragePercentage ?? 0) / 100, Colors.yellow),
              ],
            ),
          ),
        ),
        const SizedBox(width: 16),
        
        Expanded(
          child: Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: const Color(0xFF1A2D3A),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.purple.withOpacity(0.3)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Real-time Stats',
                  style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 16),
                _buildStatRow('Total Floats', '${_statistics?.totalFloats ?? 0}', Colors.cyan),
                _buildStatRow('Active Floats', '${_statistics?.activeFloats ?? 0}', Colors.green),
                _buildStatRow('Total Profiles', _formatNumber(_statistics?.totalProfiles ?? 0), Colors.orange),
                _buildStatRow('Parameters', '${_statistics?.parametersAvailable.length ?? 0} types', Colors.purple),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildHealthIndicator(String label, double value, Color color) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        children: [
          Expanded(
            flex: 2,
            child: Text(
              label,
              style: const TextStyle(color: Colors.white70, fontSize: 14),
            ),
          ),
          Expanded(
            flex: 3,
            child: LinearProgressIndicator(
              value: value,
              backgroundColor: Colors.white10,
              valueColor: AlwaysStoppedAnimation<Color>(color),
            ),
          ),
          const SizedBox(width: 8),
          Text(
            '${(value * 100).toInt()}%',
            style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w500),
          ),
        ],
      ),
    );
  }

  Widget _buildStatRow(String label, String value, Color color) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: const TextStyle(color: Colors.white70, fontSize: 14),
          ),
          Text(
            value,
            style: TextStyle(color: color, fontSize: 14, fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }

  Widget _buildChartCard(String title, Widget chart, {required double height}) {
    return Container(
      height: height,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1A2D3A),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.cyan.withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 12),
          Expanded(child: chart),
        ],
      ),
    );
  }
}
