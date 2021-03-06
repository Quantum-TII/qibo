#include "transpose_state.h"
#include "tensorflow/core/framework/op_kernel.h"

namespace tensorflow {

typedef Eigen::ThreadPoolDevice CPUDevice;
typedef Eigen::GpuDevice GPUDevice;

namespace functor {

template <typename T>
struct TransposeStateFunctor<CPUDevice, T> {
  void operator()(const OpKernelContext* context, const CPUDevice &d,
                  const std::vector<T*> state, T* transposed_state,
                  int nqubits, int ndevices, const int* qubit_order) {
    const int64 nstates = (int64) 1 << nqubits;
    const int64 npiece = (int64) nstates / ndevices;
    std::vector<int64> qubit_exponents(nqubits);
    for (int q = 0; q < nqubits; q++) {
      qubit_exponents[q] = (int64) 1 << (nqubits - qubit_order[nqubits - q - 1] - 1);
    }

    #pragma omp parallel for
    for (int64 g = 0; g < nstates; g++) {
      int64 k = 0;
      for (int q = 0; q < nqubits; q++) {
        if ((g >> q) % 2) k += qubit_exponents[q];
      }
      transposed_state[g] = state[(int64) k / npiece][(int64) k % npiece];
    }
  };
};


template <typename T>
struct SwapPiecesFunctor<CPUDevice, T> {
  void operator()(const OpKernelContext* context, const CPUDevice &d,
                  T* piece0, T* piece1, int new_global, int nqubits) {
    const int m = nqubits - new_global - 1;
    const int64 tk = (int64)1 << m;
    const int64 nstates = (int64)1 << (nqubits - 1);

    #pragma omp parallel for
    for (int64 g = 0; g < nstates; g++) {
      int64 i = ((int64)((int64)g >> m) << (m + 1)) + (g & (tk - 1));
      std::swap(piece0[i + tk], piece1[i]);
    }
  }
};


template <typename Device, typename T>
class TransposeStateOp : public OpKernel {
 public:
  explicit TransposeStateOp(OpKernelConstruction *context) : OpKernel(context) {
    OP_REQUIRES_OK(context, context->GetAttr("nqubits", &nqubits_));
    OP_REQUIRES_OK(context, context->GetAttr("ndevices", &ndevices_));
    OP_REQUIRES_OK(context, context->GetAttr("qubit_order", &qubit_order_));
    OP_REQUIRES_OK(context, context->GetAttr("omp_num_threads", &threads_));
    omp_set_num_threads(threads_);
  }

  void Compute(OpKernelContext *context) override {
    // grabe the input tensor
    std::vector<T*> state(ndevices_);
    for (int i = 0; i < ndevices_; i++) {
      state[i] = (T*) context->input(i).flat<T>().data();
    }
    Tensor transposed_state = context->input(ndevices_);

    // prevent running on GPU
    OP_REQUIRES(
        context, (std::is_same<Device, CPUDevice>::value == true),
        errors::Unimplemented("TransposeStateOp operator not implemented for GPU."));

    // call the implementation
    TransposeStateFunctor<Device, T>()(context, context->eigen_device<Device>(),
                                       state, transposed_state.flat<T>().data(),
                                       nqubits_, ndevices_, qubit_order_.data());
    context->set_output(0, transposed_state);
  }
  private:
   int nqubits_;
   int ndevices_;
   int threads_;
   std::vector<int> qubit_order_;
};


template <typename Device, typename T>
class SwapPiecesOp : public OpKernel {
 public:
  explicit SwapPiecesOp(OpKernelConstruction *context) : OpKernel(context) {
    OP_REQUIRES_OK(context, context->GetAttr("nqubits", &nqubits_));
    OP_REQUIRES_OK(context, context->GetAttr("target", &target_));
    OP_REQUIRES_OK(context, context->GetAttr("omp_num_threads", &threads_));
    omp_set_num_threads(threads_);
  }

  void Compute(OpKernelContext *context) override {
    // grabe the input tensor
    Tensor piece0 = context->input(0);
    Tensor piece1 = context->input(1);

    // prevent running on GPU
    OP_REQUIRES(
        context, (std::is_same<Device, CPUDevice>::value == true),
        errors::Unimplemented("SwapPiecesOp operator not implemented for GPU."));

    // call the implementation
    SwapPiecesFunctor<Device, T>()(context, context->eigen_device<Device>(),
                                   piece0.flat<T>().data(),
                                   piece1.flat<T>().data(),
                                   target_, nqubits_);

    context->set_output(0, piece0);
    context->set_output(1, piece1);
  }
  private:
   int nqubits_, target_, threads_;
};


// Register the CPU kernels.
#define REGISTER_TRANSPOSE_CPU(T)                                   \
  REGISTER_KERNEL_BUILDER(                                          \
      Name("TransposeState").Device(DEVICE_CPU).TypeConstraint<T>("T"), \
      TransposeStateOp<CPUDevice, T>);
REGISTER_TRANSPOSE_CPU(complex64);
REGISTER_TRANSPOSE_CPU(complex128);

#define REGISTER_SWAPPIECE_CPU(T)                                   \
  REGISTER_KERNEL_BUILDER(                                          \
      Name("SwapPieces").Device(DEVICE_CPU).TypeConstraint<T>("T"), \
      SwapPiecesOp<CPUDevice, T>);
REGISTER_SWAPPIECE_CPU(complex64);
REGISTER_SWAPPIECE_CPU(complex128);


// Register the GPU kernels.
#define REGISTER_TRANSPOSE_GPU(T)                                             \
  extern template struct TransposeStateFunctor<GPUDevice, T>;           \
  REGISTER_KERNEL_BUILDER(                                          \
      Name("TransposeState").Device(DEVICE_GPU).TypeConstraint<T>("T"), \
      TransposeStateOp<GPUDevice, T>);
REGISTER_TRANSPOSE_GPU(complex64);
REGISTER_TRANSPOSE_GPU(complex128);

#define REGISTER_SWAPPIECE_GPU(T)                                             \
  extern template struct SwapPiecesFunctor<GPUDevice, T>;           \
  REGISTER_KERNEL_BUILDER(                                          \
      Name("SwapPieces").Device(DEVICE_GPU).TypeConstraint<T>("T"), \
      SwapPiecesOp<GPUDevice, T>);
REGISTER_SWAPPIECE_GPU(complex64);
REGISTER_SWAPPIECE_GPU(complex128);
}  // namespace functor
}  // namespace tensorflow
