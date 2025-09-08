import 'package:flutter/material.dart';
import 'dart:math' as math;

class HeatmapCalendar extends StatelessWidget {
  final List<List<double>>? data;
  final int weeks;
  final int daysPerWeek;

  const HeatmapCalendar({
    super.key,
    this.data,
    this.weeks = 16,
    this.daysPerWeek = 7,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Day labels
          Row(
            children: [
              const SizedBox(width: 20),
              ...List.generate(daysPerWeek, (index) {
                final days = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];
                return Expanded(
                  child: Text(
                    days[index],
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      color: Colors.white54,
                      fontSize: 10,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                );
              }),
            ],
          ),
          const SizedBox(height: 8),
          
          // Heatmap grid
          Expanded(
            child: Column(
              children: List.generate(math.min(weeks, 12), (weekIndex) {
                return Expanded(
                  child: Row(
                    children: [
                      // Week number or month label
                      SizedBox(
                        width: 20,
                        child: weekIndex % 4 == 0
                            ? Text(
                                _getMonthLabel(weekIndex ~/ 4),
                                style: const TextStyle(
                                  color: Colors.white54,
                                  fontSize: 9,
                                ),
                              )
                            : const SizedBox(),
                      ),
                      
                      // Daily cells
                      ...List.generate(daysPerWeek, (dayIndex) {
                        final intensity = _generateIntensity(weekIndex, dayIndex);
                        return Expanded(
                          child: Container(
                            margin: const EdgeInsets.all(1),
                            decoration: BoxDecoration(
                              color: _getColorForIntensity(intensity),
                              borderRadius: BorderRadius.circular(2),
                            ),
                            child: AspectRatio(
                              aspectRatio: 1,
                              child: Container(),
                            ),
                          ),
                        );
                      }),
                    ],
                  ),
                );
              }),
            ),
          ),
          
          const SizedBox(height: 12),
          
          // Legend
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Less',
                style: TextStyle(color: Colors.white54, fontSize: 11),
              ),
              Row(
                children: List.generate(5, (index) {
                  return Container(
                    width: 10,
                    height: 10,
                    margin: const EdgeInsets.only(left: 2),
                    decoration: BoxDecoration(
                      color: _getColorForIntensity(index / 4),
                      borderRadius: BorderRadius.circular(2),
                    ),
                  );
                }),
              ),
              const Text(
                'More',
                style: TextStyle(color: Colors.white54, fontSize: 11),
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _getMonthLabel(int monthIndex) {
    final months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
    return months[monthIndex % months.length];
  }

  double _generateIntensity(int week, int day) {
    // Generate pseudo-random but consistent data for demo
    final seed = week * 7 + day;
    final random = math.Random(seed);
    
    // Create some patterns - more activity on weekdays
    var baseIntensity = day >= 1 && day <= 5 ? 0.6 : 0.3;
    baseIntensity += random.nextDouble() * 0.4;
    
    // Some seasonal variation
    if (week > 8) baseIntensity *= 0.8; // Less activity in later period
    
    return math.min(1.0, baseIntensity);
  }

  Color _getColorForIntensity(double intensity) {
    if (intensity < 0.1) return const Color(0xFF1A2D3A);
    if (intensity < 0.3) return const Color(0xFF0D4F73).withOpacity(0.4);
    if (intensity < 0.5) return const Color(0xFF0D4F73).withOpacity(0.6);
    if (intensity < 0.7) return const Color(0xFF0D4F73).withOpacity(0.8);
    return const Color(0xFF00D4FF);
  }
}
