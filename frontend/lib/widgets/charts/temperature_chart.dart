import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../../themes/app_theme.dart';

class TemperatureChart extends StatefulWidget {
  const TemperatureChart({super.key});

  @override
  State<TemperatureChart> createState() => _TemperatureChartState();
}

class _TemperatureChartState extends State<TemperatureChart> {
  @override
  Widget build(BuildContext context) {
    return LineChart(
      LineChartData(
        gridData: FlGridData(
          show: true,
          drawVerticalLine: true,
          drawHorizontalLine: true,
          getDrawingHorizontalLine: (value) {
            return const FlLine(
              color: Colors.grey,
              strokeWidth: 0.5,
            );
          },
          getDrawingVerticalLine: (value) {
            return const FlLine(
              color: Colors.grey,
              strokeWidth: 0.5,
            );
          },
        ),
        titlesData: FlTitlesData(
          show: true,
          rightTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          topTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 30,
              interval: 50,
              getTitlesWidget: (value, meta) {
                return SideTitleWidget(
                  axisSide: meta.axisSide,
                  child: Text(
                    '${value.toInt()}m',
                    style: const TextStyle(fontSize: 10),
                  ),
                );
              },
            ),
            axisNameWidget: const Text(
              'Depth',
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
            ),
          ),
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              interval: 5,
              reservedSize: 40,
              getTitlesWidget: (value, meta) {
                return SideTitleWidget(
                  axisSide: meta.axisSide,
                  child: Text(
                    '${value.toInt()}°C',
                    style: const TextStyle(fontSize: 10),
                  ),
                );
              },
            ),
            axisNameWidget: const Text(
              'Temperature',
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
            ),
          ),
        ),
        borderData: FlBorderData(
          show: true,
          border: Border.all(color: Colors.grey.shade300),
        ),
        minX: 0,
        maxX: 200,
        minY: 5,
        maxY: 30,
        lineBarsData: [
          LineChartBarData(
            spots: _generateTemperatureData(),
            isCurved: true,
            gradient: const LinearGradient(
              colors: [
                AppTheme.accent,
                AppTheme.primaryBlue,
              ],
            ),
            barWidth: 3,
            isStrokeCapRound: true,
            dotData: const FlDotData(
              show: true,
            ),
            belowBarData: BarAreaData(
              show: true,
              gradient: LinearGradient(
                colors: [
                  AppTheme.accent.withValues(alpha: 0.3),
                  AppTheme.primaryBlue.withValues(alpha: 0.1),
                ],
                begin: Alignment.centerLeft,
                end: Alignment.centerRight,
              ),
            ),
          ),
        ],
        lineTouchData: LineTouchData(
          enabled: true,
          touchTooltipData: LineTouchTooltipData(
            getTooltipItems: (List<LineBarSpot> touchedBarSpots) {
              return touchedBarSpots.map((barSpot) {
                return LineTooltipItem(
                  'Depth: ${barSpot.x.toInt()}m\nTemp: ${barSpot.y.toStringAsFixed(1)}°C',
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

  List<FlSpot> _generateTemperatureData() {
    // Mock temperature profile data (typical ARGO profile)
    return [
      const FlSpot(0, 28.5),    // Surface
      const FlSpot(10, 28.2),   // 10m
      const FlSpot(20, 27.8),   // 20m
      const FlSpot(50, 26.5),   // 50m
      const FlSpot(100, 22.3),  // 100m
      const FlSpot(150, 18.7),  // 150m
      const FlSpot(200, 15.2),  // 200m
    ];
  }
}
