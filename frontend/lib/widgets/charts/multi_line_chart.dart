import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';

class MultiLineChart extends StatelessWidget {
  const MultiLineChart({super.key});

  @override
  Widget build(BuildContext context) {
    return LineChart(
      LineChartData(
        backgroundColor: Colors.transparent,
        gridData: FlGridData(
          show: true,
          drawVerticalLine: false,
          getDrawingHorizontalLine: (value) {
            return const FlLine(
              color: Colors.white10,
              strokeWidth: 0.5,
            );
          },
        ),
        titlesData: FlTitlesData(
          show: true,
          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 30,
              interval: 1,
              getTitlesWidget: (value, meta) {
                const months = ['JAN', 'FEB', 'MARCH', 'APR', 'MAY', 'JUN'];
                if (value.toInt() >= 0 && value.toInt() < months.length) {
                  return Text(
                    months[value.toInt()],
                    style: const TextStyle(color: Colors.white54, fontSize: 10),
                  );
                }
                return const Text('');
              },
            ),
          ),
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              interval: 100,
              reservedSize: 40,
              getTitlesWidget: (value, meta) {
                return Text(
                  '\$${value.toInt()}',
                  style: const TextStyle(color: Colors.white54, fontSize: 10),
                );
              },
            ),
          ),
        ),
        borderData: FlBorderData(show: false),
        minX: 0,
        maxX: 5,
        minY: 100,
        maxY: 500,
        lineBarsData: [
          // Cyan line (Temperature)
          LineChartBarData(
            spots: [
              const FlSpot(0, 200),
              const FlSpot(1, 180),
              const FlSpot(2, 240),
              const FlSpot(3, 300),
              const FlSpot(4, 420),
              const FlSpot(5, 460),
            ],
            isCurved: true,
            gradient: const LinearGradient(
              colors: [Color(0xFF00D4FF), Color(0xFF00A8CC)],
            ),
            barWidth: 3,
            isStrokeCapRound: true,
            dotData: FlDotData(
              show: true,
              getDotPainter: (spot, percent, barData, index) {
                return FlDotCirclePainter(
                  radius: 4,
                  color: const Color(0xFF00D4FF),
                  strokeWidth: 2,
                  strokeColor: Colors.white,
                );
              },
            ),
            belowBarData: BarAreaData(
              show: true,
              gradient: LinearGradient(
                colors: [
                  const Color(0xFF00D4FF).withOpacity(0.3),
                  const Color(0xFF00D4FF).withOpacity(0.0),
                ],
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
              ),
            ),
          ),
          // Red/Orange line (Salinity)
          LineChartBarData(
            spots: [
              const FlSpot(0, 300),
              const FlSpot(1, 250),
              const FlSpot(2, 200),
              const FlSpot(3, 180),
              const FlSpot(4, 160),
              const FlSpot(5, 220),
            ],
            isCurved: true,
            gradient: const LinearGradient(
              colors: [Color(0xFFFF6B35), Color(0xFFFF8A50)],
            ),
            barWidth: 3,
            isStrokeCapRound: true,
            dotData: FlDotData(
              show: true,
              getDotPainter: (spot, percent, barData, index) {
                return FlDotCirclePainter(
                  radius: 4,
                  color: const Color(0xFFFF6B35),
                  strokeWidth: 2,
                  strokeColor: Colors.white,
                );
              },
            ),
          ),
          // Green line (Oxygen)
          LineChartBarData(
            spots: [
              const FlSpot(0, 150),
              const FlSpot(1, 200),
              const FlSpot(2, 320),
              const FlSpot(3, 380),
              const FlSpot(4, 350),
              const FlSpot(5, 400),
            ],
            isCurved: true,
            gradient: const LinearGradient(
              colors: [Color(0xFF4ECDC4), Color(0xFF44B09E)],
            ),
            barWidth: 3,
            isStrokeCapRound: true,
            dotData: FlDotData(
              show: true,
              getDotPainter: (spot, percent, barData, index) {
                return FlDotCirclePainter(
                  radius: 4,
                  color: const Color(0xFF4ECDC4),
                  strokeWidth: 2,
                  strokeColor: Colors.white,
                );
              },
            ),
          ),
        ],
        lineTouchData: LineTouchData(
          enabled: true,
          touchTooltipData: LineTouchTooltipData(
            getTooltipItems: (List<LineBarSpot> touchedBarSpots) {
              return touchedBarSpots.map((barSpot) {
                final flSpot = barSpot;
                return LineTooltipItem(
                  '${flSpot.y.toInt()}°C',
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
}
