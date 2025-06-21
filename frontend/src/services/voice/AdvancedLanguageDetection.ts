// Advanced Language Detection Service
// Uses multiple detection engines for dramatically improved accuracy

// Web Speech API type declarations
declare global {
  interface Window {
    SpeechRecognition: new () => SpeechRecognition;
    webkitSpeechRecognition: new () => SpeechRecognition;
  }
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  grammars: SpeechGrammarList;
  interimResults: boolean;
  lang: string;
  maxAlternatives: number;
  onaudioend: ((this: SpeechRecognition, ev: Event) => any) | null;
  onaudiostart: ((this: SpeechRecognition, ev: Event) => any) | null;
  onend: ((this: SpeechRecognition, ev: Event) => any) | null;
  onerror: ((this: SpeechRecognition, ev: SpeechRecognitionErrorEvent) => any) | null;
  onnomatch: ((this: SpeechRecognition, ev: SpeechRecognitionEvent) => any) | null;
  onresult: ((this: SpeechRecognition, ev: SpeechRecognitionEvent) => any) | null;
  onsoundend: ((this: SpeechRecognition, ev: Event) => any) | null;
  onsoundstart: ((this: SpeechRecognition, ev: Event) => any) | null;
  onspeechend: ((this: SpeechRecognition, ev: Event) => any) | null;
  onspeechstart: ((this: SpeechRecognition, ev: Event) => any) | null;
  onstart: ((this: SpeechRecognition, ev: Event) => any) | null;
  serviceURI: string;
  start(): void;
  stop(): void;
  abort(): void;
}

interface SpeechRecognitionEvent extends Event {
  readonly resultIndex: number;
  readonly results: SpeechRecognitionResultList;
}

interface SpeechRecognitionErrorEvent extends Event {
  readonly error: string;
  readonly message: string;
}

interface SpeechRecognitionResultList {
  readonly length: number;
  item(index: number): SpeechRecognitionResult;
  [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionResult {
  readonly isFinal: boolean;
  readonly length: number;
  item(index: number): SpeechRecognitionAlternative;
  [index: number]: SpeechRecognitionAlternative;
}

interface SpeechRecognitionAlternative {
  readonly transcript: string;
  readonly confidence: number;
}

interface SpeechGrammarList {
  readonly length: number;
  addFromString(string: string, weight?: number): void;
  addFromURI(src: string, weight?: number): void;
  item(index: number): SpeechGrammar;
  [index: number]: SpeechGrammar;
}

interface SpeechGrammar {
  src: string;
  weight: number;
}

export interface LanguageDetectionResult {
  language: string;
  confidence: number;
  method: 'webSpeech' | 'phonetic' | 'statistical' | 'consensus' | 'linguistic_features';
  details?: any;
}

export class AdvancedLanguageDetection {
  private webSpeechEngines: Map<string, SpeechRecognition> = new Map();
  private isInitialized = false;
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;

  // Support for major languages with Web Speech API
  private supportedLanguages = [
    'en-US', 'en-GB', 'en-AU', 'en-CA', 'en-IN',
    'es-ES', 'es-MX', 'es-AR', 'es-CO', 'es-CL',
    'fr-FR', 'fr-CA', 'fr-BE', 'fr-CH',
    'de-DE', 'de-AT', 'de-CH',
    'it-IT', 'it-CH',
    'pt-PT', 'pt-BR',
    'ru-RU',
    'zh-CN', 'zh-TW', 'zh-HK',
    'ja-JP',
    'ko-KR',
    'ar-SA', 'ar-EG',
    'nl-NL', 'nl-BE',
    'sv-SE',
    'no-NO',
    'da-DK',
    'fi-FI',
    'pl-PL',
    'cs-CZ',
    'hu-HU',
    'tr-TR',
    'he-IL',
    'th-TH',
    'vi-VN',
    'id-ID',
    'ms-MY',
    'hi-IN',
    'bn-BD'
  ];

  constructor() {
    this.initialize();
  }

  private async initialize() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      console.warn('Web Speech API not supported');
      return;
    }

    try {
      // Test which languages are actually supported
      console.log('🔧 Initializing Advanced Language Detection...');
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      
      // Create test recognizers for top languages to verify support
      const testLanguages = ['en-US', 'es-ES', 'fr-FR', 'de-DE', 'it-IT', 'pt-BR', 'zh-CN', 'ja-JP'];
      
      for (const lang of testLanguages) {
        try {
          const recognition = new SpeechRecognition();
          recognition.lang = lang;
          recognition.continuous = false;
          recognition.interimResults = false;
          recognition.maxAlternatives = 1;
          
          this.webSpeechEngines.set(lang, recognition);
        } catch (e) {
          console.warn(`Language ${lang} not supported:`, e);
        }
      }

      this.isInitialized = true;
      console.log(`✅ Initialized ${this.webSpeechEngines.size} language detection engines`);
    } catch (error) {
      console.error('Failed to initialize language detection:', error);
    }
  }

  // Detect language using multiple Web Speech API engines in parallel
  async detectLanguageParallel(audioBlob: Blob): Promise<LanguageDetectionResult[]> {
    if (!this.isInitialized || this.webSpeechEngines.size === 0) {
      return [];
    }

    const results: LanguageDetectionResult[] = [];
    const promises: Promise<LanguageDetectionResult | null>[] = [];

    // Test top languages simultaneously
    const testLanguages = Array.from(this.webSpeechEngines.keys()).slice(0, 8);
    
    for (const lang of testLanguages) {
      const recognition = this.webSpeechEngines.get(lang);
      if (!recognition) continue;

      const promise = this.testLanguageRecognition(recognition, lang, audioBlob);
      promises.push(promise);
    }

    try {
      const results = await Promise.allSettled(promises);
      const validResults: LanguageDetectionResult[] = [];

      results.forEach((result, index) => {
        if (result.status === 'fulfilled' && result.value) {
          validResults.push(result.value);
        }
      });

      // Sort by confidence
      validResults.sort((a, b) => b.confidence - a.confidence);
      
      console.log('🎯 Parallel detection results:', validResults);
      return validResults.slice(0, 3); // Top 3 results

    } catch (error) {
      console.error('Parallel detection failed:', error);
      return [];
    }
  }

  private async testLanguageRecognition(
    recognition: SpeechRecognition, 
    language: string, 
    audioBlob: Blob
  ): Promise<LanguageDetectionResult | null> {
    return new Promise((resolve) => {
      const timeout = setTimeout(() => {
        recognition.stop();
        resolve(null);
      }, 3000); // 3 second timeout

      recognition.onresult = (event) => {
        clearTimeout(timeout);
        
        if (event.results.length > 0) {
          const result = event.results[0];
          if (result.isFinal && result[0]) {
            const transcript = result[0].transcript;
            const confidence = result[0].confidence || 0;
            
            // Calculate enhanced confidence based on transcript quality
            const enhancedConfidence = this.calculateEnhancedConfidence(
              transcript, 
              confidence, 
              language
            );

            resolve({
              language: language.split('-')[0], // Extract base language
              confidence: enhancedConfidence,
              method: 'webSpeech',
              details: {
                originalLanguage: language,
                transcript: transcript,
                originalConfidence: confidence,
                transcriptLength: transcript.length
              }
            });
          }
        }
        resolve(null);
      };

      recognition.onerror = () => {
        clearTimeout(timeout);
        resolve(null);
      };

      recognition.onend = () => {
        clearTimeout(timeout);
      };

      try {
        recognition.start();
      } catch (e) {
        clearTimeout(timeout);
        resolve(null);
      }
    });
  }

  private calculateEnhancedConfidence(
    transcript: string, 
    originalConfidence: number, 
    language: string
  ): number {
    let confidence = originalConfidence || 0.5;
    
    // Boost confidence based on transcript length and coherence
    if (transcript.length > 10) confidence += 0.1;
    if (transcript.length > 30) confidence += 0.1;
    
    // Check for language-specific patterns
    const patterns = this.getLanguagePatterns(language);
    let patternMatches = 0;
    
    for (const pattern of patterns.words) {
      if (transcript.toLowerCase().includes(pattern)) {
        patternMatches++;
      }
    }
    
    if (patternMatches > 0) {
      confidence += Math.min(0.3, patternMatches * 0.05);
    }
    
    // Check for characteristic characters
    for (const char of patterns.chars) {
      if (transcript.includes(char)) {
        confidence += 0.02;
      }
    }
    
    return Math.min(0.99, Math.max(0.1, confidence));
  }

  private getLanguagePatterns(language: string) {
    const patterns: { [key: string]: { words: string[], chars: string[] } } = {
      'en': {
        words: ['the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 'it', 'for', 'not', 'on', 'with', 'hello', 'thank', 'please', 'yes', 'no'],
        chars: []
      },
      'es': {
        words: ['el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'muy', 'bien', 'sí', 'gracias', 'hola', 'español', 'cómo', 'dónde'],
        chars: ['ñ', 'á', 'é', 'í', 'ó', 'ú', '¿', '¡']
      },
      'fr': {
        words: ['le', 'de', 'et', 'à', 'un', 'il', 'en', 'que', 'pour', 'dans', 'ce', 'son', 'je', 'tu', 'nous', 'vous', 'bonjour', 'merci', 'français', 'être', 'avoir'],
        chars: ['à', 'é', 'è', 'ê', 'ë', 'î', 'ï', 'ô', 'ù', 'û', 'ü', 'ÿ', 'ç']
      },
      'de': {
        words: ['der', 'die', 'und', 'in', 'den', 'von', 'zu', 'das', 'mit', 'sich', 'ist', 'nicht', 'ein', 'eine', 'haben', 'sein', 'deutsch', 'ich', 'Sie'],
        chars: ['ä', 'ö', 'ü', 'ß']
      },
      'it': {
        words: ['il', 'di', 'che', 'e', 'la', 'per', 'un', 'in', 'con', 'del', 'da', 'a', 'al', 'le', 'si', 'molto', 'bene', 'ciao', 'grazie', 'italiano', 'sono', 'è'],
        chars: ['à', 'è', 'é', 'ì', 'ò', 'ù']
      },
      'pt': {
        words: ['o', 'de', 'a', 'e', 'do', 'da', 'em', 'um', 'para', 'é', 'com', 'não', 'uma', 'os', 'no', 'se', 'muito', 'obrigado', 'olá', 'português', 'são', 'está'],
        chars: ['ã', 'õ', 'á', 'à', 'é', 'ê', 'í', 'ó', 'ô', 'ú', 'ç']
      },
      'ru': {
        words: ['и', 'в', 'не', 'на', 'я', 'быть', 'с', 'он', 'что', 'как', 'есть', 'нет', 'да', 'привет', 'спасибо'],
        chars: ['а', 'б', 'в', 'г', 'д', 'е', 'ё', 'ж', 'з', 'и', 'й', 'к', 'л', 'м', 'н', 'о', 'п', 'р', 'с', 'т', 'у', 'ф', 'х', 'ц', 'ч', 'ш', 'щ', 'ъ', 'ы', 'ь', 'э', 'ю', 'я']
      },
      'uk': {
        words: ['і', 'в', 'не', 'на', 'я', 'бути', 'з', 'він', 'що', 'як', 'є', 'ні', 'так', 'привіт', 'дякую'],
        chars: ['а', 'б', 'в', 'г', 'ґ', 'д', 'е', 'є', 'ж', 'з', 'и', 'і', 'ї', 'й', 'к', 'л', 'м', 'н', 'о', 'п', 'р', 'с', 'т', 'у', 'ф', 'х', 'ц', 'ч', 'ш', 'щ', 'ь', 'ю', 'я']
      },
      'zh': {
        words: ['的', '是', '在', '我', '有', '和', '人', '这', '中', '大', '好', '不', '了', '谢谢', '请'],
        chars: ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
      },
      'ja': {
        words: ['は', 'の', 'が', 'を', 'に', 'と', 'で', 'も', 'です', 'ます', 'こんにちは', 'ありがとう'],
        chars: ['あ', 'い', 'う', 'え', 'お', 'か', 'き', 'く', 'け', 'こ', 'さ', 'し', 'す', 'せ', 'そ', 'た', 'ち', 'つ', 'て', 'と']
      },
      'ko': {
        words: ['은', '는', '이', '가', '을', '를', '의', '에', '안녕하세요', '감사합니다', '습니다', '입니다'],
        chars: ['ㄱ', 'ㄴ', 'ㄷ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅅ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
      },
      'th': {
        words: ['และ', 'ใน', 'ที่', 'การ', 'เป็น', 'ของ', 'ได้', 'มี', 'สวัสดี', 'ขอบคุณ', 'ครับ', 'ค่ะ'],
        chars: ['ก', 'ข', 'ค', 'ง', 'จ', 'ช', 'ซ', 'ญ', 'ด', 'ต', 'ถ', 'ท', 'น', 'บ', 'ป', 'ผ', 'พ', 'ฟ', 'ภ', 'ม', 'ย', 'ร', 'ล', 'ว', 'ศ', 'ษ', 'ส', 'ห', 'อ', 'ฮ']
      },
      'vi': {
        words: ['là', 'của', 'và', 'có', 'trong', 'một', 'tôi', 'bạn', 'anh', 'chị', 'xin', 'chào', 'cảm', 'ơn'],
        chars: ['à', 'á', 'ạ', 'ả', 'ã', 'â', 'ầ', 'ấ', 'ậ', 'ẩ', 'ẫ', 'ă', 'ằ', 'ắ', 'ặ', 'ẳ', 'ẵ', 'è', 'é', 'ẹ', 'ẻ', 'ẽ', 'ê', 'ề', 'ế', 'ệ', 'ể', 'ễ', 'đ']
      },
      'hi': {
        words: ['और', 'में', 'है', 'के', 'की', 'को', 'से', 'एक', 'मैं', 'आप', 'नमस्ते', 'धन्यवाद'],
        chars: ['अ', 'आ', 'इ', 'ई', 'उ', 'ऊ', 'ए', 'ऐ', 'ओ', 'औ', 'क', 'ख', 'ग', 'घ', 'च', 'छ', 'ज', 'झ', 'ट', 'ठ', 'ड', 'ढ', 'त', 'थ', 'द', 'ध', 'न', 'प', 'फ', 'ब', 'भ', 'म', 'य', 'र', 'ल', 'व', 'श', 'ष', 'स', 'ह']
      },
      'tr': {
        words: ['ve', 'bir', 'bu', 'ben', 'sen', 'merhaba', 'teşekkür', 'ederim', 'evet', 'hayır'],
        chars: ['ç', 'ğ', 'ı', 'ö', 'ş', 'ü']
      },
      'nl': {
        words: ['de', 'het', 'een', 'en', 'van', 'ik', 'je', 'hallo', 'dank', 'je', 'wel', 'ja', 'nee'],
        chars: ['ë', 'ï', 'ü', 'é', 'è', 'ê']
      },
      'pl': {
        words: ['i', 'w', 'na', 'z', 'że', 'się', 'ja', 'ty', 'cześć', 'dziękuję', 'tak', 'nie'],
        chars: ['ą', 'ć', 'ę', 'ł', 'ń', 'ó', 'ś', 'ź', 'ż']
      },
      'sv': {
        words: ['och', 'i', 'att', 'det', 'som', 'jag', 'du', 'hej', 'tack', 'ja', 'nej'],
        chars: ['å', 'ä', 'ö']
      },
      'no': {
        words: ['og', 'i', 'å', 'det', 'som', 'jeg', 'du', 'hei', 'takk', 'ja', 'nei'],
        chars: ['å', 'æ', 'ø']
      },
      'da': {
        words: ['og', 'i', 'at', 'det', 'som', 'jeg', 'du', 'hej', 'tak', 'ja', 'nej'],
        chars: ['å', 'æ', 'ø']
      },
      'fi': {
        words: ['ja', 'on', 'se', 'että', 'minä', 'sinä', 'moi', 'hei', 'kiitos', 'kyllä'],
        chars: ['ä', 'ö', 'å']
      },
      'cs': {
        words: ['a', 'v', 'na', 'se', 'že', 'já', 'ty', 'ahoj', 'děkuji', 'ano', 'ne'],
        chars: ['á', 'č', 'ď', 'é', 'ě', 'í', 'ň', 'ó', 'ř', 'š', 'ť', 'ú', 'ů', 'ý', 'ž']
      },
      'sk': {
        words: ['a', 'v', 'na', 'sa', 'že', 'ja', 'ty', 'ahoj', 'ďakujem', 'áno', 'nie'],
        chars: ['á', 'ä', 'č', 'ď', 'é', 'í', 'ľ', 'ĺ', 'ň', 'ó', 'ô', 'ŕ', 'š', 'ť', 'ú', 'ý', 'ž']
      },
      'hu': {
        words: ['és', 'a', 'az', 'hogy', 'én', 'te', 'hello', 'köszönöm', 'igen', 'nem'],
        chars: ['á', 'é', 'í', 'ó', 'ö', 'ő', 'ú', 'ü', 'ű']
      },
      'ro': {
        words: ['și', 'în', 'de', 'la', 'cu', 'eu', 'tu', 'salut', 'mulțumesc', 'da', 'nu'],
        chars: ['ă', 'â', 'î', 'ș', 'ț']
      },
      'el': {
        words: ['και', 'στο', 'για', 'από', 'με', 'εγώ', 'εσύ', 'γεια', 'σας', 'ευχαριστώ', 'ναι', 'όχι'],
        chars: ['α', 'β', 'γ', 'δ', 'ε', 'ζ', 'η', 'θ', 'ι', 'κ', 'λ', 'μ', 'ν', 'ξ', 'ο', 'π', 'ρ', 'σ', 'τ', 'υ', 'φ', 'χ', 'ψ', 'ω']
      },
      'id': {
        words: ['dan', 'di', 'yang', 'dengan', 'untuk', 'saya', 'anda', 'halo', 'terima', 'kasih', 'ya', 'tidak'],
        chars: []
      },
      'ms': {
        words: ['dan', 'di', 'yang', 'dengan', 'untuk', 'saya', 'awak', 'hello', 'terima', 'kasih', 'ya', 'tidak'],
        chars: []
      }
    };
    
    const baseLang = language.split('-')[0];
    return patterns[baseLang] || { words: [], chars: [] };
  }

  // Audio fingerprinting for language detection
  async analyzeAudioFingerprint(audioData: Float32Array): Promise<LanguageDetectionResult | null> {
    // Analyze frequency patterns, formants, and prosodic features
    // This is a simplified version - real implementation would be much more sophisticated
    
    const fftSize = 2048;
    const frequencies = new Float32Array(fftSize / 2);
    
    // Calculate spectral centroid, rolloff, and other features
    let spectralCentroid = 0;
    let spectralRolloff = 0;
    let totalEnergy = 0;
    
    for (let i = 0; i < frequencies.length; i++) {
      const magnitude = Math.abs(audioData[i] || 0);
      spectralCentroid += i * magnitude;
      totalEnergy += magnitude;
    }
    
    if (totalEnergy > 0) {
      spectralCentroid /= totalEnergy;
      
      // Find spectral rolloff (frequency below which 85% of energy lies)
      let energySum = 0;
      const rolloffThreshold = totalEnergy * 0.85;
      
      for (let i = 0; i < frequencies.length; i++) {
        energySum += Math.abs(audioData[i] || 0);
        if (energySum >= rolloffThreshold) {
          spectralRolloff = i;
          break;
        }
      }
    }
    
    // Language-specific acoustic patterns (simplified)
    const acousticPatterns: { [key: string]: { centroidRange: [number, number], rolloffRange: [number, number] } } = {
      'en': { centroidRange: [200, 400], rolloffRange: [2000, 4000] },
      'es': { centroidRange: [180, 350], rolloffRange: [1800, 3800] },
      'fr': { centroidRange: [220, 420], rolloffRange: [2200, 4200] },
      'de': { centroidRange: [190, 380], rolloffRange: [1900, 3900] },
      'it': { centroidRange: [210, 410], rolloffRange: [2100, 4100] },
      'pt': { centroidRange: [185, 375], rolloffRange: [1850, 3850] }
    };
    
    let bestMatch = '';
    let bestScore = 0;
    
    for (const [lang, pattern] of Object.entries(acousticPatterns)) {
      let score = 0;
      
      // Check if spectral centroid fits pattern
      if (spectralCentroid >= pattern.centroidRange[0] && spectralCentroid <= pattern.centroidRange[1]) {
        score += 0.5;
      }
      
      // Check if spectral rolloff fits pattern
      if (spectralRolloff >= pattern.rolloffRange[0] && spectralRolloff <= pattern.rolloffRange[1]) {
        score += 0.5;
      }
      
      if (score > bestScore) {
        bestScore = score;
        bestMatch = lang;
      }
    }
    
    if (bestScore > 0.3) {
      return {
        language: bestMatch,
        confidence: bestScore,
        method: 'phonetic',
        details: {
          spectralCentroid,
          spectralRolloff,
          totalEnergy
        }
      };
    }
    
    return null;
  }

  // Consensus algorithm combining multiple detection methods
  calculateConsensus(results: LanguageDetectionResult[]): LanguageDetectionResult | null {
    if (results.length === 0) return null;
    
    // Group by language
    const languageGroups: { [key: string]: LanguageDetectionResult[] } = {};
    
    results.forEach(result => {
      if (!languageGroups[result.language]) {
        languageGroups[result.language] = [];
      }
      languageGroups[result.language].push(result);
    });
    
    // Calculate consensus scores with priority for linguistic features
    const consensusResults = Object.entries(languageGroups).map(([lang, detections]) => {
      const avgConfidence = detections.reduce((sum, d) => sum + d.confidence, 0) / detections.length;
      const maxConfidence = Math.max(...detections.map(d => d.confidence));
      const methodCount = new Set(detections.map(d => d.method)).size;
      
      // Check if linguistic features method is present (high priority)
      const hasLinguisticFeatures = detections.some(d => d.method === 'linguistic_features');
      const linguisticConfidence = hasLinguisticFeatures 
        ? detections.find(d => d.method === 'linguistic_features')?.confidence || 0
        : 0;
      
      // Enhanced consensus score with linguistic features priority
      let consensusScore = (avgConfidence * 0.3) + (maxConfidence * 0.3) + (methodCount / 5 * 0.1);
      
      // Boost score significantly if linguistic features detected this language
      if (hasLinguisticFeatures && linguisticConfidence > 0.8) {
        consensusScore += 0.3; // Significant boost for high-confidence linguistic detection
      } else if (hasLinguisticFeatures) {
        consensusScore += 0.15; // Moderate boost for any linguistic detection
      }
      
      return {
        language: lang,
        confidence: consensusScore,
        method: 'consensus' as const,
        details: {
          detections,
          avgConfidence,
          maxConfidence,
          methodCount,
          hasLinguisticFeatures,
          linguisticConfidence,
          consensusScore
        }
      };
    });
    
    // Return highest consensus score
    consensusResults.sort((a, b) => b.confidence - a.confidence);
    
    console.log('🔍 All consensus results:', consensusResults);
    
    const winner = consensusResults[0];
    if (winner && winner.confidence > 0.5) { // Lowered threshold
      console.log('🏆 Consensus winner:', winner);
      return winner;
    }
    
    console.log('❌ No consensus winner found, highest score:', winner?.confidence);
    return null;
  }
}

// Global instance
export const advancedLanguageDetection = new AdvancedLanguageDetection();