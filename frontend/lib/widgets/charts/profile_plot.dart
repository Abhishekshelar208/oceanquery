import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../../themes/app_theme.dart';

class ProfilePlot extends StatefulWidget {
  final String? profileId;
  final String? floatId;
  final String primaryParameter;
  final String? secondaryParameter;
  final bool showComparison;

  const ProfilePlot({
    super.key,
    this.profileId,
    this.floatId,
    this.primaryParameter = 'temperature',
    this.secondaryParameter,
    this.showComparison = false,
  });

  @override
  State<ProfilePlot> createState() => _ProfilePlotState();
}

class _ProfilePlotState extends State<ProfilePlot> {
  List<Map<String, dynamic>> _profileData = [];
  bool _isLoading = true;
  String? _error;
  String _selectedPrimaryParameter = 'temperature';
  String? _selectedSecondaryParameter;
  bool _showComparison = false;
  
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
    _selectedPrimaryParameter = widget.primaryParameter;
    _selectedSecondaryParameter = widget.secondaryParameter;
    _showComparison = widget.showComparison;
    _loadProfileData();
  }

  Future<void> _loadProfileData() async {
    try {
      setState(() {
        _isLoading = true;
        _error = null;
      });
      
      // For now, generate mock profile data until backend endpoint is ready
      final data = _generateMockProfileData();
      
      setState(() {
        _profileData = data;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  List<Map<String, dynamic>> _generateMockProfileData() {
    final List<Map<String, dynamic>> data = [];
    
    for (int i = 0; i <= 50; i++) {
      final depth = i * 40.0; // 0 to 2000m depth
      
      // Generate realistic oceanographic profiles
      final temperature = _generateTemperatureAtDepth(depth);
      final salinity = _generateSalinityAtDepth(depth);
      final pressure = depth / 10.0; // Rough approximation
      final oxygen = _generateOxygenAtDepth(depth);
      
      data.add({
        'depth': depth,
        'temperature': temperature,
        'salinity': salinity,
        'pressure': pressure,
        'oxygen': oxygen,
      });
    }
    
    return data;
  }

  double _generateTemperatureAtDepth(double depth) {
    // Realistic temperature profile for Indian Ocean
    if (depth <= 50) {
      return 28.0 - (depth * 0.04); // Surface mixed layer
    } else if (depth <= 200) {
      return 26.0 - ((depth - 50) * 0.067); // Thermocline
    } else if (depth <= 1000) {
      return 16.0 - ((depth - 200) * 0.0125); // Deep water
    } else {
      return 6.0 - ((depth - 1000) * 0.002); // Abyssal
    }
  }

  double _generateSalinityAtDepth(double depth) {
    // Realistic salinity profile
    if (depth <= 50) {
      return 34.5 + (depth * 0.004); // Surface layer
    } else if (depth <= 500) {
      return 34.7 + ((depth - 50) * 0.0004); // Subsurface
    } else {
      return 34.9 + ((depth - 500) * 0.00002); // Deep water
    }
  }

  double _generateOxygenAtDepth(double depth) {
    // Realistic oxygen profile with minimum zone
    if (depth <= 100) {
      return 220.0 - (depth * 0.8); // Surface decline
    } else if (depth <= 800) {
      return 140.0 - ((depth - 100) * 0.114); // Oxygen minimum zone
    } else {
      return 60.0 + ((depth - 800) * 0.05); // Deep water increase
    }
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
            _buildParameterControls(),
            const SizedBox(height: 20),
            _buildProfileChart(),
            const SizedBox(height: 16),
            _buildLegend(),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Row(
      children: [
        Icon(
          Icons.waves,
          color: AppTheme.primaryBlue,
          size: 24,
        ),
        const SizedBox(width: 8),
        Text(
          'Ocean Profile',
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
            fontWeight: FontWeight.bold,
            color: AppTheme.primaryBlue,
          ),
        ),
        if (widget.profileId != null) ...[
          const SizedBox(width: 8),
          Text(
            'ID: ${widget.profileId}',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Colors.grey[600],
            ),
          ),
        ],
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

  Widget _buildParameterControls() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.science, size: 16, color: AppTheme.primaryBlue),
            const SizedBox(width: 8),
            Text(
              'Primary Parameter:',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: AppTheme.primaryBlue,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          children: _parameterColors.keys.map((parameter) {
            final isSelected = parameter == _selectedPrimaryParameter;
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
                    _selectedPrimaryParameter = parameter;
                  });
                  _loadProfileData();
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
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Checkbox(
              value: _showComparison,
              onChanged: (value) {
                setState(() {
                  _showComparison = value ?? false;
                  if (!_showComparison) {
                    _selectedSecondaryParameter = null;
                  }
                });
              },
            ),
            Text(
              'Show comparison parameter',
              style: TextStyle(color: AppTheme.primaryBlue),
            ),
          ],
        ),
        if (_showComparison) ...[
          const SizedBox(height: 8),
          Text(
            'Secondary Parameter:',
            style: TextStyle(
              fontWeight: FontWeight.bold,
              color: AppTheme.primaryBlue,
            ),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: _parameterColors.keys
                .where((p) => p != _selectedPrimaryParameter)
                .map((parameter) {
              final isSelected = parameter == _selectedSecondaryParameter;
              return FilterChip(
                label: Text(
                  parameter.toUpperCase(),
                  style: TextStyle(
                    color: isSelected ? Colors.white : Colors.grey[600],
                  ),
                ),
                selected: isSelected,
                selectedColor: _parameterColors[parameter],
                onSelected: (selected) {
                  setState(() {
                    _selectedSecondaryParameter = selected ? parameter : null;
                  });
                  _loadProfileData();
                },
              );
            }).toList(),
          ),
        ],
      ],
    );
  }

  Widget _buildProfileChart() {
    if (_isLoading) {
      return const SizedBox(
        height: 400,
        child: Center(child: CircularProgressIndicator()),
      );
    }

    if (_error != null) {
      return SizedBox(
        height: 400,
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error, color: Colors.red, size: 48),
              const SizedBox(height: 16),
              Text('Error: $_error'),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: _loadProfileData,
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }

    if (_profileData.isEmpty) {
      return const SizedBox(
        height: 400,
        child: Center(child: Text('No profile data available')),
      );
    }

    return SizedBox(
      height: 400,
      child: Row(
        children: [
          Expanded(
            child: _buildPrimaryChart(),
          ),
          if (_showComparison && _selectedSecondaryParameter != null) ...[
            const SizedBox(width: 16),
            Expanded(
              child: _buildSecondaryChart(),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildPrimaryChart() {
    final primaryData = _profileData.map((data) {
      return FlSpot(
        data[_selectedPrimaryParameter].toDouble(),
        -data['depth'].toDouble(), // Negative for inverted y-axis
      );
    }).toList();

    final primaryColor = _parameterColors[_selectedPrimaryParameter]!;
    final primaryUnit = _parameterUnits[_selectedPrimaryParameter] ?? '';

    return LineChart(
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
            axisNameWidget: Text(
              '${_selectedPrimaryParameter.toUpperCase()} ($primaryUnit)',
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
            ),
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 40,
              getTitlesWidget: (value, meta) {
                return SideTitleWidget(
                  axisSide: meta.axisSide,
                  child: Text(
                    '${value.toStringAsFixed(1)}$primaryUnit',
                    style: const TextStyle(fontSize: 10),
                  ),
                );
              },
            ),
          ),
          leftTitles: AxisTitles(
            axisNameWidget: const Text(
              'Depth (m)',
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
            ),
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 50,
              getTitlesWidget: (value, meta) {
                return SideTitleWidget(
                  axisSide: meta.axisSide,
                  child: Text(
                    '${(-value).toInt()}m', // Convert back to positive
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
            spots: primaryData,
            isCurved: false,
            color: primaryColor,
            barWidth: 3,
            isStrokeCapRound: true,
            dotData: const FlDotData(show: false),
            belowBarData: BarAreaData(show: false),
          ),
        ],
        lineTouchData: LineTouchData(
          enabled: true,
          touchTooltipData: LineTouchTooltipData(
            getTooltipItems: (touchedSpots) {
              return touchedSpots.map((barSpot) {
                final depth = (-barSpot.y).toInt();
                final value = barSpot.x;
                
                return LineTooltipItem(
                  'Depth: ${depth}m\n${_selectedPrimaryParameter.toUpperCase()}: ${value.toStringAsFixed(2)}$primaryUnit',
                  const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                  ),
                );
              }).toList();
            },
          ),
        ),
      ),
    );
  }

  Widget _buildSecondaryChart() {
    if (_selectedSecondaryParameter == null) return const SizedBox();

    final secondaryData = _profileData.map((data) {
      return FlSpot(
        data[_selectedSecondaryParameter!].toDouble(),
        -data['depth'].toDouble(),
      );
    }).toList();

    final secondaryColor = _parameterColors[_selectedSecondaryParameter!]!;
    final secondaryUnit = _parameterUnits[_selectedSecondaryParameter!] ?? '';

    return LineChart(
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
          leftTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          bottomTitles: AxisTitles(
            axisNameWidget: Text(
              '${_selectedSecondaryParameter!.toUpperCase()} ($secondaryUnit)',
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
            ),
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 40,
              getTitlesWidget: (value, meta) {
                return SideTitleWidget(
                  axisSide: meta.axisSide,
                  child: Text(
                    '${value.toStringAsFixed(1)}$secondaryUnit',
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
            spots: secondaryData,
            isCurved: false,
            color: secondaryColor,
            barWidth: 3,
            isStrokeCapRound: true,
            dotData: const FlDotData(show: false),
            belowBarData: BarAreaData(show: false),
          ),
        ],
        lineTouchData: LineTouchData(
          enabled: true,
          touchTooltipData: LineTouchTooltipData(
            getTooltipItems: (touchedSpots) {
              return touchedSpots.map((barSpot) {
                final depth = (-barSpot.y).toInt();
                final value = barSpot.x;
                
                return LineTooltipItem(
                  'Depth: ${depth}m\n${_selectedSecondaryParameter!.toUpperCase()}: ${value.toStringAsFixed(2)}$secondaryUnit',
                  const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                  ),
                );
              }).toList();
            },
          ),
        ),
      ),
    );
  }

  Widget _buildLegend() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Profile Information',
          style: TextStyle(
            fontWeight: FontWeight.bold,
            color: AppTheme.primaryBlue,
          ),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Container(
              width: 16,
              height: 3,
              color: _parameterColors[_selectedPrimaryParameter],
            ),
            const SizedBox(width: 8),
            Text('${_selectedPrimaryParameter.toUpperCase()} profile'),
            if (_showComparison && _selectedSecondaryParameter != null) ...[
              const SizedBox(width: 20),
              Container(
                width: 16,
                height: 3,
                color: _parameterColors[_selectedSecondaryParameter!],
              ),
              const SizedBox(width: 8),
              Text('${_selectedSecondaryParameter!.toUpperCase()} profile'),
            ],
          ],
        ),
        const SizedBox(height: 8),
        Text(
          'Data points: ${_profileData.length} | Max depth: ${_profileData.isNotEmpty ? _profileData.last['depth'].toInt() : 0}m',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: Colors.grey[600],
          ),
        ),
      ],
    );
  }
}
