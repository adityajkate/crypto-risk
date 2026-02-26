import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

interface RiskGaugeProps {
  value: number; // 0 to 100
  label: string;
}

const RiskGauge: React.FC<RiskGaugeProps> = ({ value, label }) => {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current) return;

    const width = 200;
    const height = 120; // Semi-circle
    const radius = Math.min(width, height * 2) / 2;
    const innerRadius = radius - 30;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); // Clear previous renders

    const g = svg
      .attr('viewBox', `0 0 ${width} ${height}`)
      .append('g')
      .attr('transform', `translate(${width / 2},${height})`);

    // Define color scale
    const colorScale = d3.scaleLinear<string>()
      .domain([0, 50, 100])
      .range(['#10b981', '#f59e0b', '#ef4444']); // Green, Yellow, Red

    // Background Arc (full semicircle)
    const backgroundArc = d3.arc<d3.DefaultArcObject>()
      .innerRadius(innerRadius)
      .outerRadius(radius)
      .startAngle(-Math.PI / 2)
      .endAngle(Math.PI / 2);

    g.append('path')
      .datum({} as any)
      .attr('d', backgroundArc as any)
      .style('fill', '#e5e7eb');

    // Value Arc - CRITICAL: Ensure accurate mapping from value (0-100) to angle
    // -Math.PI/2 is 0%, Math.PI/2 is 100%
    // Total range is Math.PI (180 degrees)
    const valueAngle = -Math.PI / 2 + (Math.PI * value) / 100;

    const valueArc = d3.arc<d3.DefaultArcObject>()
      .innerRadius(innerRadius)
      .outerRadius(radius)
      .startAngle(-Math.PI / 2)
      .endAngle(valueAngle);

    g.append('path')
      .datum({} as any)
      .attr('d', valueArc as any)
      .style('fill', colorScale(value));

  }, [value, label]);

  return <svg ref={svgRef} className="w-full h-auto max-w-[200px]" />;
};

export default RiskGauge;
