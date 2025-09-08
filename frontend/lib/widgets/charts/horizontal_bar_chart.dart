import 'package:flutter/material.dart';

class HorizontalBarChart extends StatefulWidget {
  final List<BarData>? data;

  const HorizontalBarChart({
    super.key,
    this.data,
  });

  @override
  State<HorizontalBarChart> createState() => _HorizontalBarChartState();
}

class _HorizontalBarChartState extends State<HorizontalBarChart>
    with SingleTickerProviderStateMixin {
  late AnimationController _animationController;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    );
    _animation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _animationController, curve: Curves.easeOut),
    );
    _animationController.forward();
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  List<BarData> get chartData => widget.data ?? [
    BarData('Pacific Ocean', 1247, Colors.blue),
    BarData('Atlantic Ocean', 892, Colors.cyan),
    BarData('Indian Ocean', 653, Colors.orange),
    BarData('Arctic Ocean', 234, Colors.purple),
    BarData('Southern Ocean', 387, Colors.green),
  ];

  @override
  Widget build(BuildContext context) {
    final maxValue = chartData.map((e) => e.value).reduce((a, b) => a > b ? a : b);
    
    return AnimatedBuilder(
      animation: _animation,
      builder: (context, child) {
        return Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              // Legend
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'Region',
                    style: TextStyle(color: Colors.white54, fontSize: 12),
                  ),
                  const Text(
                    'Active Floats',
                    style: TextStyle(color: Colors.white54, fontSize: 12),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              
              // Bars
              Expanded(
                child: ListView.separated(
                  itemCount: chartData.length,
                  separatorBuilder: (context, index) => const SizedBox(height: 16),
                  itemBuilder: (context, index) {
                    final data = chartData[index];
                    final percentage = data.value / maxValue;
                    final animatedWidth = percentage * _animation.value;
                    
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Label and value
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              data.label,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 14,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                            Text(
                              data.value.toString(),
                              style: TextStyle(
                                color: data.color,
                                fontSize: 14,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        
                        // Progress bar
                        Container(
                          height: 8,
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: FractionallySizedBox(
                            alignment: Alignment.centerLeft,
                            widthFactor: animatedWidth,
                            child: Container(
                              decoration: BoxDecoration(
                                gradient: LinearGradient(
                                  colors: [
                                    data.color,
                                    data.color.withOpacity(0.7),
                                  ],
                                  begin: Alignment.centerLeft,
                                  end: Alignment.centerRight,
                                ),
                                borderRadius: BorderRadius.circular(4),
                                boxShadow: [
                                  BoxShadow(
                                    color: data.color.withOpacity(0.4),
                                    blurRadius: 4,
                                    offset: const Offset(0, 2),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                        
                        // Percentage indicator
                        const SizedBox(height: 4),
                        Text(
                          '${(percentage * 100).toInt()}%',
                          style: TextStyle(
                            color: data.color.withOpacity(0.8),
                            fontSize: 11,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    );
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class BarData {
  final String label;
  final double value;
  final Color color;

  const BarData(this.label, this.value, this.color);
}
