import cffi

ffi = cffi.FFI()
ffi.set_source("_amzi", None)

ffi.cdef("""
typedef enum
{
   pERR = -1,
   pATOM,
   pINT,
   pSTR,
   pFLOAT,
   pSTRUCT,
   pLIST,
   pTERM,
   pADDR,
   pVAR,
   pWSTR,
   pWATOM,
	pREAL
} pTYPE;

typedef enum
{
   cAATOM,
   cASTR,
   cINT,
   cLONG,
   cSHORT,
   cFLOAT,
   cDOUBLE,
   cADDR,
   cTERM,
   cWSTR,
   cWATOM,
   // used to break apart :/2 structures
   cMOD,
   cGOAL
} cTYPE;

typedef enum
{
   CUR_IN,
   CUR_OUT,
   CUR_ERR,
   USER_IN,
   USER_OUT,
   USER_ERR
} STREAM;

typedef   void *      VOIDptr;
typedef unsigned short  uintCH;
typedef uintCH     ARITY;
typedef ARITY *    ARITYptr;

typedef void * ENGid;
typedef ENGid * ENGidptr;
typedef void* TERM;
typedef TERM *     TERMptr;

typedef int (*ExtPred)(VOIDptr);

typedef struct {
     wchar_t*   Pname;
     ARITY      Parity;
     ExtPred    Pfunc;
} PRED_INITW;
typedef PRED_INITW * PRED_INITWptr;

int lsInitW(ENGidptr, wchar_t*);
int lsLoadW(ENGid, wchar_t*);
int lsCallStrW(ENGid, TERMptr, wchar_t*);
int lsExecStrW(ENGid, TERMptr, wchar_t*);
pTYPE lsGetTermType(ENGid, TERM);
pTYPE lsGetArgType(ENGid, TERM, int);
int lsGetArg(ENGid, TERM, int, cTYPE, VOIDptr);
int lsGetFAW(ENGid, TERM, wchar_t*, ARITYptr);
int lsTermToStrW(ENGid, TERM, wchar_t*, int);
int lsStrToTermW(ENGid, TERMptr, wchar_t*);
int lsGetTerm(ENGid, TERM, cTYPE, VOIDptr);
int lsGetHead(ENGid, TERM, cTYPE, VOIDptr);
int lsClearCall(ENGid);
TERM lsGetTail(ENGid, TERM);
int lsRedo(ENGid);
int lsMain(ENGid);
int lsClose(ENGid);
int lsSetStream(ENGid, STREAM, int);
int lsSetOutputW(ENGid, void *, void *);
int lsAssertzStrW(ENGid, wchar_t*);
int lsAssertaStrW(ENGid, wchar_t*);
int lsInitPredsW(ENGid, PRED_INITWptr);
int lsAddPredW(ENGid, wchar_t*, ARITY, ExtPred, VOIDptr);
int lsGetParm(ENGid, int, cTYPE, VOIDptr);
int lsUnifyParm(ENGid, int, cTYPE, VOIDptr);
int lsUnify(ENGid, TERM, TERM);
int lsMakeAtomW(ENGid, TERMptr, wchar_t*);
int lsMakeStrW(ENGid, TERMptr, wchar_t*);
int lsMakeInt(ENGid, TERMptr, long);
int lsMakeFloat(ENGid, TERMptr, double);
int lsMakeList(ENGid, TERMptr);
int lsPushList(ENGid, TERMptr, TERM);
int lsMakeFAW(ENGid, TERMptr, wchar_t*, ARITY);
int lsUnifyArg(ENGid, TERMptr, int, cTYPE, VOIDptr);
void lsGetExceptMsgW(ENGid, wchar_t*, int);
""")

def main():
    ffi.compile(verbose=True)

if __name__ == '__main__':
    import sys
    sys.exit(int(main() or 0))