import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../../themes/app_theme.dart';

class TimeSeriesChart extends StatefulWidget {
  final String parameter;
  final String? floatId;
  final DateTime? startDate;
  final DateTime? endDate;
  final double? minDepth;
  final double? maxDepth;

  const TimeSeriesChart({
    super.key,
    this.parameter = 'temperature',
    this.floatId,
    this.startDate,
    this.endDate,
    this.minDepth,
    this.maxDepth,
  });

  @override
  State<TimeSeriesChart> createState() => _TimeSeriesChartState();
}

class _TimeSeriesChartState extends State<TimeSeriesChart> {
  List<Map<String, dynamic>> _timeSeriesData = [];
  bool _isLoading = true;
  String? _error;
  String _selectedParameter = 'temperature';
  DateTime? _selectedStartDate;
  DateTime? _selectedEndDate;
  
  final Map<String, Color> _parameterColors = {
    'temperature': AppTheme.accent,
    'salinity': AppTheme.primaryBlue,
    'pressure': Colors.purple,
    'oxygen': Colors.green,
  };
  
  final Map<String, String> _parameterUnits = {
    'temperature': '°C',
    'salinity': 'PSU', 
    'pressure': 'dbar',
    'oxygen': 'μmol/kg',
  };

  @override
  void initState() {
    super.initState();
    _selectedParameter = widget.parameter;
    _selectedStartDate = widget.startDate ?? DateTime.now().subtract(const Duration(days: 30));
    _selectedEndDate = widget.endDate ?? DateTime.now();
    _loadTimeSeriesData();
  }

  Future<void> _loadTimeSeriesData() async {
    try {
      setState(() {
        _isLoading = true;
        _error = null;
      });
      
      // For now, generate mock time series data until backend endpoint is ready
      final data = _generateMockTimeSeriesData();
      
      setState(() {
        _timeSeriesData = data;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  List<Map<String, dynamic>> _generateMockTimeSeriesData() {
    final List<Map<String, dynamic>> data = [];
    final startTime = _selectedStartDate ?? DateTime.now().subtract(const Duration(days: 30));
    final endTime = _selectedEndDate ?? DateTime.now();
    final duration = endTime.difference(startTime);
    
    for (int i = 0; i < 50; i++) {
      final date = startTime.add(Duration(milliseconds: (duration.inMilliseconds * i / 49).round()));
      
      double value;
      switch (_selectedParameter) {
        case 'temperature':
          value = 25.0 + (5.0 * (0.5 - (i / 100.0))) + (2.0 * (0.5 - DateTime.now().millisecondsSinceEpoch % 100 / 100.0));
          break;
        case 'salinity':
          value = 35.0 + (2.0 * (0.5 - (i / 100.0))) + (1.0 * (0.5 - DateTime.now().millisecondsSinceEpoch % 100 / 100.0));
          break;
        case 'pressure':
          value = 100.0 + (50.0 * (i / 50.0)) + (10.0 * (0.5 - DateTime.now().millisecondsSinceEpoch % 100 / 100.0));
          break;
        case 'oxygen':
          value = 200.0 + (50.0 * (0.5 - (i / 100.0))) + (20.0 * (0.5 - DateTime.now().millisecondsSinceEpoch % 100 / 100.0));
          break;
        default:
          value = 0.0;
      }
      
      data.add({
        'date': date,
        'value': value,
        'depth': 10.0 + (i * 2.0), // Mock depth progression
      });
    }
    
    return data;
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildHeader(),
            const SizedBox(height: 16),
            _buildParameterSelector(),
            const SizedBox(height: 16),
            _buildDateRangeSelector(),
            const SizedBox(height: 20),
            _buildChart(),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Row(
      children: [
        Icon(
          Icons.trending_up,
          color: AppTheme.primaryBlue,
          size: 24,
        ),
        const SizedBox(width: 8),
        Text(
          'Time Series Analysis',
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
            fontWeight: FontWeight.bold,
            color: AppTheme.primaryBlue,
          ),
        ),
        const Spacer(),
        if (_isLoading)
          const SizedBox(
            width: 20,
            height: 20,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
      ],
    );
  }

  Widget _buildParameterSelector() {
    return Wrap(
      spacing: 8,
      children: _parameterColors.keys.map((parameter) {
        final isSelected = parameter == _selectedParameter;
        return FilterChip(
          label: Text(
            parameter.toUpperCase(),
            style: TextStyle(
              color: isSelected ? Colors.white : AppTheme.primaryBlue,
              fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
            ),
          ),
          selected: isSelected,
          selectedColor: _parameterColors[parameter],
          onSelected: (selected) {
            if (selected) {
              setState(() {
                _selectedParameter = parameter;
              });
              _loadTimeSeriesData();
            }
          },
          avatar: Container(
            width: 12,
            height: 12,
            decoration: BoxDecoration(
              color: _parameterColors[parameter],
              shape: BoxShape.circle,
            ),
          ),
        );
      }).toList(),
    );
  }

  Widget _buildDateRangeSelector() {
    return Row(
      children: [
        Icon(Icons.calendar_today, size: 16, color: AppTheme.primaryBlue),
        const SizedBox(width: 8),
        TextButton(
          onPressed: () => _selectDateRange(),
          child: Text(
            '${_selectedStartDate?.toLocal().toString().split(' ')[0]} - ${_selectedEndDate?.toLocal().toString().split(' ')[0]}',
            style: TextStyle(color: AppTheme.primaryBlue),
          ),
        ),
        const Spacer(),
        Text(
          '${_timeSeriesData.length} data points',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: Colors.grey[600],
          ),
        ),
      ],
    );
  }

  Widget _buildChart() {
    if (_isLoading) {
      return const SizedBox(
        height: 300,
        child: Center(child: CircularProgressIndicator()),
      );
    }

    if (_error != null) {
      return SizedBox(
        height: 300,
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error, color: Colors.red, size: 48),
              const SizedBox(height: 16),
              Text('Error: $_error'),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: _loadTimeSeriesData,
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }

    if (_timeSeriesData.isEmpty) {
      return const SizedBox(
        height: 300,
        child: Center(child: Text('No data available for selected parameters')),
      );
    }

    return SizedBox(
      height: 300,
      child: LineChart(
        LineChartData(
          gridData: FlGridData(
            show: true,
            drawVerticalLine: true,
            drawHorizontalLine: true,
            getDrawingHorizontalLine: (value) => const FlLine(
              color: Colors.grey,
              strokeWidth: 0.5,
            ),
            getDrawingVerticalLine: (value) => const FlLine(
              color: Colors.grey,
              strokeWidth: 0.5,
            ),
          ),
          titlesData: FlTitlesData(
            show: true,
            rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 40,
                interval: (_timeSeriesData.length / 5).ceil().toDouble(),
                getTitlesWidget: (value, meta) {
                  final index = value.toInt();
                  if (index >= 0 && index < _timeSeriesData.length) {
                    final date = _timeSeriesData[index]['date'] as DateTime;
                    return SideTitleWidget(
                      axisSide: meta.axisSide,
                      child: Text(
                        '${date.month}/${date.day}',
                        style: const TextStyle(fontSize: 10),
                      ),
                    );
                  }
                  return const SizedBox();
                },
              ),
            ),
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 50,
                getTitlesWidget: (value, meta) {
                  final unit = _parameterUnits[_selectedParameter] ?? '';
                  return SideTitleWidget(
                    axisSide: meta.axisSide,
                    child: Text(
                      '${value.toStringAsFixed(1)}$unit',
                      style: const TextStyle(fontSize: 10),
                    ),
                  );
                },
              ),
            ),
          ),
          borderData: FlBorderData(
            show: true,
            border: Border.all(color: Colors.grey.shade300),
          ),
          lineBarsData: [
            LineChartBarData(
              spots: _timeSeriesData
                  .asMap()
                  .entries
                  .map((entry) => FlSpot(
                        entry.key.toDouble(),
                        entry.value['value'].toDouble(),
                      ))
                  .toList(),
              isCurved: true,
              gradient: LinearGradient(
                colors: [
                  _parameterColors[_selectedParameter]!.withValues(alpha: 0.8),
                  _parameterColors[_selectedParameter]!,
                ],
              ),
              barWidth: 3,
              isStrokeCapRound: true,
              dotData: FlDotData(
                show: _timeSeriesData.length <= 20, // Only show dots for small datasets
              ),
              belowBarData: BarAreaData(
                show: true,
                gradient: LinearGradient(
                  colors: [
                    _parameterColors[_selectedParameter]!.withValues(alpha: 0.3),
                    _parameterColors[_selectedParameter]!.withValues(alpha: 0.1),
                  ],
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                ),
              ),
            ),
          ],
          lineTouchData: LineTouchData(
            enabled: true,
            touchTooltipData: LineTouchTooltipData(
              getTooltipItems: (touchedSpots) {
                return touchedSpots.map((barSpot) {
                  final index = barSpot.x.toInt();
                  if (index >= 0 && index < _timeSeriesData.length) {
                    final data = _timeSeriesData[index];
                    final date = data['date'] as DateTime;
                    final value = data['value'];
                    final unit = _parameterUnits[_selectedParameter] ?? '';
                    
                    return LineTooltipItem(
                      '${date.month}/${date.day}/${date.year}\n${_selectedParameter.toUpperCase()}: ${value.toStringAsFixed(2)}$unit',
                      const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                      ),
                    );
                  }
                  return null;
                }).where((item) => item != null).cast<LineTooltipItem>().toList();
              },
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _selectDateRange() async {
    final DateTimeRange? picked = await showDateRangePicker(
      context: context,
      firstDate: DateTime(2020, 1, 1),
      lastDate: DateTime.now(),
      initialDateRange: DateTimeRange(
        start: _selectedStartDate ?? DateTime.now().subtract(const Duration(days: 30)),
        end: _selectedEndDate ?? DateTime.now(),
      ),
    );
    
    if (picked != null) {
      setState(() {
        _selectedStartDate = picked.start;
        _selectedEndDate = picked.end;
      });
      _loadTimeSeriesData();
    }
  }
}
