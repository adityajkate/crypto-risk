import React from 'react';

interface IndicatorTooltipProps {
  label: string;
  description: string;
}

const IndicatorTooltip: React.FC<IndicatorTooltipProps> = ({ label, description }) => {
  return <span>{label}</span>;
};

export default IndicatorTooltip;
