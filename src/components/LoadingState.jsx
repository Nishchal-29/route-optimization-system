import { Loader2, Sparkles, MapPin, Route } from 'lucide-react';

export default function LoadingState() {
  return (
    <div className="card">
      <div className="flex flex-col items-center justify-center py-12">
        <div className="relative">
          <div className="w-20 h-20 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
          <Loader2 className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-8 h-8 text-primary-500" />
        </div>
        
        <h3 className="text-xl font-semibold mt-6 text-gray-800">
          Optimizing Your Route
        </h3>
        
        <div className="mt-6 space-y-3 text-center max-w-md">
          <div className="flex items-center gap-3 text-sm text-gray-600">
            <Sparkles className="w-5 h-5 text-primary-500 animate-pulse" />
            <span>Analyzing locations with AI...</span>
          </div>
          <div className="flex items-center gap-3 text-sm text-gray-600">
            <MapPin className="w-5 h-5 text-primary-500 animate-pulse delay-100" />
            <span>Calculating distances...</span>
          </div>
          <div className="flex items-center gap-3 text-sm text-gray-600">
            <Route className="w-5 h-5 text-primary-500 animate-pulse delay-200" />
            <span>Finding optimal sequence...</span>
          </div>
        </div>

        <div className="mt-6 w-full max-w-md bg-gray-200 rounded-full h-2 overflow-hidden">
          <div className="bg-gradient-to-r from-primary-500 to-secondary-500 h-full rounded-full animate-pulse" 
               style={{ width: '60%' }} />
        </div>
        
        <p className="text-sm text-gray-500 mt-4">
          This may take a few seconds...
        </p>
      </div>
    </div>
  );
}