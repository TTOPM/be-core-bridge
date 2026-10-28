import type { AcousticModelProfile, DuplexModelAdapter } from './types.ts';
/** No model weights bundled, no vendor endpoint or credentials configured. */
export const BELEL_MODEL_CANDIDATES: readonly AcousticModelProfile[] = Object.freeze([
  Object.freeze({ id:'kyutai-moshi', family:'moshi', capabilities:['native-speech-dialogue','full-duplex','streaming-audio','interruptions'], weightsLicense:'CC-BY-4.0; verify checkpoint terms', requiresSeparateDeployment:true, approvedForProduction:false, officialUrl:'https://github.com/kyutai-labs/moshi' }),
  Object.freeze({ id:'nvidia-personaplex', family:'personaplex', capabilities:['full-duplex','speaker-conditioned-output','persona-control','streaming-audio'], weightsLicense:'NVIDIA Open Model License; acceptance required', requiresSeparateDeployment:true, approvedForProduction:false, officialUrl:'https://github.com/NVIDIA/personaplex' }),
  Object.freeze({ id:'block-dessa-future', family:'future-dessa', capabilities:['research-reference-only'], weightsLicense:'No public weights / licensed API confirmed as of 2026-10-28', requiresSeparateDeployment:true, approvedForProduction:false, officialUrl:'https://block.xyz/dessa' }),
]);
export class BelelModelRegistry {
  private models = new Map<string, DuplexModelAdapter>();
  private approved = new Set<string>();
  register(adapter: DuplexModelAdapter): void {
    if (this.models.has(adapter.id)) throw new Error('Model already registered');
    this.models.set(adapter.id, adapter);
  }
  /** Approval must follow an actual owner/licensing/security review; never enabled by registration. */
  approve(id: string, review: { ownerApproved: boolean; licenseReviewed: boolean; selfHosted: boolean }): void {
    if (!this.models.has(id)) throw new Error('Unknown model');
    if (!review.ownerApproved || !review.licenseReviewed || !review.selfHosted) throw new Error('Model must pass owner, licence and sovereignty review');
    this.approved.add(id);
  }
  use(id: string): DuplexModelAdapter {
    if (!this.approved.has(id)) throw new Error('Model not authorised');
    const model = this.models.get(id);
    if (!model) throw new Error('Unknown model');
    return model;
  }
  listApproved(): string[] { return [...this.approved]; }
  revoke(id:string):void { this.approved.delete(id); }
}
